"""
Test Runs API routes for managing test execution and results
"""

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from typing import List
import json
import os
import csv
from pathlib import Path
import sys
from datetime import datetime
import asyncio
from services.integration import KATIntegrationService

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from ..models import (
    CreateRunRequest, RunSummary, RunDetail, RunArtifact, ApiResponse,
    DryRunRequest, DryRunResponse
)
from ..database import DatabaseManager

router = APIRouter()


async def execute_test_run(db_manager: DatabaseManager, service_id: str, run_id: str, run_config: dict):
    """Background task to execute test run"""
    try:
        # Update run status to running
        db_manager.update_run_status(run_id, "running")
        
        service_data = db_manager.get_service(service_id)
        service_dir = Path(service_data["working_dir"])
        
        # Integrate with SequenceRunner for actual test execution
        try:
            service = db_manager.get_service(service_id)
            if service:
                kat_service = KATIntegrationService(service_id, service["name"])
                # Run tests using SequenceRunner
                test_result = kat_service.run_tests(
                    base_url=run_config.get("base_url", "https://api.example.com"),
                    token=run_config.get("token"),
                    endpoint_filter=run_config.get("endpoint_filter"),
                    out_file_name=run_id
                )
                
                if test_result.get("success"):
                    # Build path of the CSV produced by SequenceRunner (flat layout)
                    results_dir = service_dir / "results"
                    results_dir.mkdir(exist_ok=True)
                    results_csv = results_dir / f"{run_id}.csv"

                    if not results_csv.exists():
                        # Nếu runner thành công nhưng không thấy CSV -> coi là failed mềm
                        db_manager.update_run_status(run_id, "failed", {"error": f"results file not found: {results_csv.name}"})
                        return

                    # Tính summary nhanh từ CSV
                    summary = _analyze_csv_results(results_csv)

                    # Cập nhật DB: completed + artifacts
                    db_manager.update_run(run_id, {
                        "status": "completed",
                        "started_at": datetime.now().isoformat() if not db_manager.get_run(run_id).get("started_at") else db_manager.get_run(run_id)["started_at"],
                        "completed_at": datetime.now().isoformat(),
                        "results": summary,
                        "artifacts": [
                            {
                                "name": "results.csv",
                                "path": str(results_csv),
                                "size": results_csv.stat().st_size,
                            }
                        ],
                        "config": {**run_config}
                    })
                    return
                    # SequenceRunner completed successfully
                    pass
                else:
                    # Log SequenceRunner error but continue with simulation for now
                    print(f"SequenceRunner failed: {test_result.get('error')}")
        except Exception as e:
            print(f"Failed to run SequenceRunner: {e}")
        
    except Exception as e:
        # Update run status to failed
        db_manager.update_run_status(run_id, "failed", {"error": str(e)})


@router.post("/services/{service_id}/runs", response_model=ApiResponse)
async def create_run(request: Request, service_id: str, run_request: CreateRunRequest, background_tasks: BackgroundTasks):
    """Create and start a new test run"""
    try:
        db_manager: DatabaseManager = request.app.state.db
        service_data = db_manager.get_service(service_id)
        
        if not service_data:
            raise HTTPException(status_code=404, detail="Service not found")
        
        # Create run configuration
        run_config = {
            "base_url": run_request.base_url,
            "token": run_request.token,
            "endpoint_filter": run_request.endpoint_filter,
            "test_case_filter": run_request.test_case_filter
        }
        
        # Create run in database
        run_id = db_manager.create_run(service_id, run_config)
        
        # Start background execution
        background_tasks.add_task(execute_test_run, db_manager, service_id, run_id, run_config)
        
        return ApiResponse(
            success=True,
            message="Test run created and started",
            data={"run_id": run_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create run: {str(e)}")


@router.get("/services/{service_id}/runs", response_model=ApiResponse)
async def list_runs(request: Request, service_id: str):
    """List all runs for a service"""
    try:
        db_manager: DatabaseManager = request.app.state.db
        service_data = db_manager.get_service(service_id)
        
        if not service_data:
            raise HTTPException(status_code=404, detail="Service not found")
        
        # Get runs from database metadata
        runs_data = db_manager.get_service_runs(service_id)
        
        # Also discover runs from results directory
        service_dir = Path(service_data["working_dir"])
        results_dir = service_dir / "results"
        
        discovered_runs = []
        if results_dir.exists():
            # Look for CSV files that might be run results
            for csv_file in results_dir.glob("*.csv"):
                run_id = csv_file.stem
                
                # Check if already in database
                existing_run = next((r for r in runs_data if r["id"] == run_id), None)
                if not existing_run:
                    # Create run entry from discovered file
                    discovered_runs.append({
                        "id": run_id,
                        "service_id": service_id,
                        "status": "completed",
                        "created_at": datetime.fromtimestamp(csv_file.stat().st_mtime).isoformat(),
                        "started_at": None,
                        "completed_at": datetime.fromtimestamp(csv_file.stat().st_mtime).isoformat(),
                        "results": _analyze_csv_results(csv_file),
                        "config": {"discovered": True}
                    })
        
        all_runs = runs_data + discovered_runs
        
        runs = [
            RunSummary(
                id=run["id"],
                service_id=run["service_id"],
                status=run["status"],
                created_at=run["created_at"],
                started_at=run.get("started_at"),
                completed_at=run.get("completed_at"),
                results=run["results"],
                config=run["config"]
            )
            for run in all_runs
        ]
        
        return ApiResponse(
            success=True,
            message="Runs retrieved successfully",
            data=runs
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve runs: {str(e)}")


import re

_STATUS_RE = re.compile(r"^(?:[1-5]xx|[1-5]\d{2}|[1-5]\d{2}-[1-5]\d{2})$", re.IGNORECASE)

def _matches_expected(actual: str | int | None, expected: str | None) -> bool:
    if actual is None or expected is None:
        return False
    try:
        actual_code = int(str(actual).strip())
    except ValueError:
        return False

    e = str(expected).strip().lower()
    if not e or not _STATUS_RE.match(e):
        return False

    if e.endswith("xx"):  # '2xx'
        lo = int(e[0]) * 100
        return lo <= actual_code < lo + 100
    if "-" in e:          # '200-299'
        a, b = e.split("-", 1)
        try:
            lo, hi = int(a), int(b)
            return lo <= actual_code <= hi
        except ValueError:
            return False
    else:                 # '404'
        try:
            return actual_code == int(e)
        except ValueError:
            return False

def _analyze_csv_results(csv_file: Path) -> dict:
    """Analyze CSV results to get summary statistics"""
    try:
        with open(csv_file, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            rows = [r for r in reader if any(v and str(v).strip() for v in r.values())]  # bỏ dòng trống

        total = len(rows)

        def row_passed(row: dict) -> bool:
            # 1) Ưu tiên cột 'status' nếu có
            st = (row.get('status') or row.get('result') or '').strip().upper()
            if st:
                return st in {'PASS', 'PASSED', 'SUCCESS', 'OK'}
            # 2) Fallback: so khớp response_status vs expected_status
            return _matches_expected(row.get('response_status'), row.get('expected_status'))

        passed = sum(1 for row in rows if row_passed(row))
        failed = total - passed
        success_rate = round((passed / total * 100), 2) if total else 0.0

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "success_rate": success_rate
        }
    except Exception as e:
        # optional: log e
        return {"total": 0, "passed": 0, "failed": 0, "success_rate": 0}



@router.get("/services/{service_id}/runs/{run_id}", response_model=ApiResponse)
async def get_run(request: Request, service_id: str, run_id: str):
    """Get detailed information about a specific run"""
    try:
        db_manager: DatabaseManager = request.app.state.db
        service_data = db_manager.get_service(service_id)
        
        if not service_data:
            raise HTTPException(status_code=404, detail="Service not found")
        
        # Try to get run from database first
        run_data = db_manager.get_run(run_id)
        # If not in database, try to discover from results directory
        service_dir = Path(service_data["working_dir"])
        results_dir = service_dir / "results"
        
        # Look for CSV file matching run_id
        csv_file = results_dir / f"{run_id}.csv"
        if csv_file.exists():
            print(f"Discovered run {run_id} from CSV file ")
            run_data = {
                "id": run_id,
                "service_id": service_id,
                "status": "completed",
                "created_at": datetime.fromtimestamp(csv_file.stat().st_mtime).isoformat(),
                "started_at": None,
                "completed_at": datetime.fromtimestamp(csv_file.stat().st_mtime).isoformat(),
                "results": _analyze_csv_results(csv_file),
                "config": {"discovered": True}
            }
        else:
            raise HTTPException(status_code=404, detail=f"csv not found at dir {csv_file}")
        
        if not run_data or run_data["service_id"] != service_id:
            raise HTTPException(status_code=404, detail="Run not found")
        
        # Get artifacts from results directory
        service_dir = Path(service_data["working_dir"])
        results_dir = service_dir / "results"
        # Build artifacts (ưu tiên DB)
        artifacts = []
        if run_data.get("artifacts"):
            for a in run_data["artifacts"]:
                p = Path(a["path"])
                if p.exists():
                    artifacts.append(RunArtifact(
                        name=a.get("name", p.name),
                        path=str(p),
                        url=f"/services/{service_id}/runs/{run_id}/artifacts/{p.name}",
                        size=p.stat().st_size,
                        created_at=datetime.fromtimestamp(p.stat().st_mtime).isoformat()
                    ))
        else:
            # Fallback: tự tìm file theo layout mới results/<run_id>.csv
            csv_file = Path(service_data["working_dir"]) / "results" / f"{run_id}.csv"
            if csv_file.exists():
                artifacts.append(RunArtifact(
                    name="results.csv",
                    path=str(csv_file),
                    url=f"/services/{service_id}/runs/{run_id}/artifacts/results.csv",
                    size=csv_file.stat().st_size,
                    created_at=datetime.fromtimestamp(csv_file.stat().st_mtime).isoformat()
                ))

        
        # Response JSON files in output directory
        output_dir = results_dir / "output"
        if output_dir.exists():
            for response_dir in output_dir.iterdir():
                if response_dir.is_dir():
                    for json_file in response_dir.glob("*.json"):
                        artifacts.append(RunArtifact(
                            name=f"responses/{response_dir.name}/{json_file.name}",
                            path=str(json_file),
                            url=f"/services/{service_id}/runs/{run_id}/artifacts/{response_dir.name}/{json_file.name}",
                            size=json_file.stat().st_size,
                            created_at=datetime.fromtimestamp(json_file.stat().st_mtime).isoformat()
                        ))
        
        # Get logs if available
        logs = []
        log_file = results_dir / f"{run_id}.log"
        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = f.readlines()
        
        run_detail = RunDetail(
            id=run_data["id"],
            service_id=run_data["service_id"],
            status=run_data["status"],
            created_at=run_data["created_at"],
            started_at=run_data.get("started_at"),
            completed_at=run_data.get("completed_at"),
            results=run_data["results"],
            config=run_data["config"],
            artifacts=artifacts,
            logs=logs
        )
        
        return ApiResponse(
            success=True,
            message="Run details retrieved successfully",
            data=run_detail
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve run: {str(e)}")


@router.get("/services/{service_id}/runs/{run_id}/results", response_model=ApiResponse)
async def get_run_results(request: Request, service_id: str, run_id: str):
    """Get detailed test results for a run"""
    try:
        db_manager: DatabaseManager = request.app.state.db
        run_data = db_manager.get_run(run_id)
        if not run_data or run_data["service_id"] != service_id:
            raise HTTPException(status_code=404, detail="Run not found")

        service_data = db_manager.get_service(service_id)
        service_dir = Path(service_data["working_dir"])
        results_root = service_dir / "results"

        detailed_results = []

        # Support BOTH layouts:
        # A) /results/<run_id>/results.csv
        # B) /results/<run_id>.csv
        per_run_dir = results_root / run_id
        csv_in_dir = per_run_dir / "results.csv"
        flat_csv = results_root / f"{run_id}.csv"

        results_csv = None
        if csv_in_dir.exists():
            results_csv = csv_in_dir
        elif flat_csv.exists():
            results_csv = flat_csv

        if results_csv and results_csv.exists():
            with open(results_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                detailed_results = list(reader)

        # Attach response JSONs if present (only if folder layout exists)
        if per_run_dir.exists() and per_run_dir.is_dir():
            for json_file in per_run_dir.glob("*.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        response_data = json.load(f)
                    # Map JSON file to the matching test row by prefix
                    for row in detailed_results:
                        tc = row.get("test_case", "") or row.get("id", "")
                        if tc and json_file.stem.startswith(tc):
                            row["response_data"] = response_data
                            break
                except Exception:
                    continue

        return ApiResponse(
            success=True,
            message="Detailed results retrieved successfully",
            data={
                "run_summary": run_data["results"],
                "detailed_results": detailed_results
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve results: {str(e)}")

@router.delete("/services/{service_id}/runs/{run_id}", response_model=ApiResponse)
async def delete_run(request: Request, service_id: str, run_id: str):
    """Delete a test run and its results"""
    try:
        db_manager: DatabaseManager = request.app.state.db
        run_data = db_manager.get_run(run_id)
        
        if not run_data or run_data["service_id"] != service_id:
            raise HTTPException(status_code=404, detail="Run not found")
        
        # Delete run files
        service_data = db_manager.get_service(service_id)
        results_dir = Path(service_data["working_dir"]) / "results" / run_id
        if results_dir.exists():
            import shutil
            shutil.rmtree(results_dir)
        
        # Remove from database
        data = db_manager.load_data()
        if run_id in data["runs"]:
            del data["runs"][run_id]
            db_manager.save_data(data)
        
        return ApiResponse(
            success=True,
            message="Run deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete run: {str(e)}")


@router.post("/services/{service_id}/test-cases/{test_case_id}/run", response_model=ApiResponse)
async def run_single_test_case(request: Request, service_id: str, test_case_id: str, run_request: CreateRunRequest):
    """Run a single test case using SequenceRunner"""
    try:
        db_manager: DatabaseManager = request.app.state.db
        service_data = db_manager.get_service(service_id)
        
        if not service_data:
            raise HTTPException(status_code=404, detail="Service not found")
        
        # Use KAT integration to run single test case
        try:
            from services.integration import KATIntegrationService
            service = db_manager.get_service(service_id)
            if not service:
                raise HTTPException(status_code=404, detail="Service not found")
                
            kat_service = KATIntegrationService(service_id, service["name"])
            
            # Run single test case
            result = kat_service.run_single_test_case(
                test_case_id=test_case_id,
                base_url=run_request.base_url,
                token=run_request.token
            )
            
            if result.get("success"):
                return ApiResponse(
                    success=True,
                    message=f"Test case executed successfully: {result.get('result')}",
                    data={
                        "test_case_id": test_case_id,
                        "test_passed": result.get("test_passed"),
                        "test_case_file": result.get("test_case_file"),
                        "result": result.get("result")
                    }
                )
            else:
                raise HTTPException(status_code=500, detail=f"Test execution failed: {result.get('error')}")
                
        except ImportError as ie:
            raise HTTPException(status_code=500, detail="SequenceRunner components not available")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to execute test case: {str(e)}")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run test case: {str(e)}")


@router.post("/services/{service_id}/dry-run", response_model=ApiResponse)
async def dry_run(request: Request, service_id: str, dry_run_request: DryRunRequest):
    """Perform a dry run of a single endpoint for debugging"""
    try:
        db_manager: DatabaseManager = request.app.state.db
        service_data = db_manager.get_service(service_id)
        
        if not service_data:
            raise HTTPException(status_code=404, detail="Service not found")
        
        # TODO: Integrate with actual request building logic
        # For now, simulate URL building
        
        method, path = dry_run_request.endpoint.split('-', 1) if '-' in dry_run_request.endpoint else ('GET', dry_run_request.endpoint)
        
        # Build URL
        base_url = dry_run_request.base_url.rstrip('/')
        full_url = f"{base_url}{path}"
        
        # Prepare headers
        headers = {"Content-Type": "application/json"}
        if dry_run_request.headers:
            headers.update(dry_run_request.headers)
        
        # Validate parameters and body
        validation_errors = []
        
        # Basic validation
        if not dry_run_request.base_url:
            validation_errors.append("Base URL is required")
        
        if method.upper() in ['POST', 'PUT', 'PATCH'] and not dry_run_request.body:
            validation_errors.append(f"{method.upper()} requests typically require a body")
        
        dry_run_response = DryRunResponse(
            url=full_url,
            method=method.upper(),
            headers=headers,
            body=dry_run_request.body,
            params=dry_run_request.params,
            validation_errors=validation_errors if validation_errors else None
        )
        
        return ApiResponse(
            success=True,
            message="Dry run completed successfully",
            data=dry_run_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to perform dry run: {str(e)}")


@router.get("/services/{service_id}/artifacts", response_model=ApiResponse)
async def list_artifacts(request: Request, service_id: str):
    """List all artifacts for a service"""
    try:
        db_manager: DatabaseManager = request.app.state.db
        service_data = db_manager.get_service(service_id)
        
        if not service_data:
            raise HTTPException(status_code=404, detail="Service not found")
        
        service_dir = Path(service_data["working_dir"])
        artifacts = []
        
        # List all artifacts from results directory
        results_dir = service_dir / "results"
        if results_dir.exists():
            for run_dir in results_dir.iterdir():
                if run_dir.is_dir():
                    for artifact_file in run_dir.iterdir():
                        if artifact_file.is_file():
                            artifacts.append({
                                "name": artifact_file.name,
                                "path": str(artifact_file),
                                "run_id": run_dir.name,
                                "url": f"/api/v1/services/{service_id}/artifacts/{run_dir.name}/{artifact_file.name}",
                                "size": artifact_file.stat().st_size,
                                "created_at": datetime.fromtimestamp(artifact_file.stat().st_mtime).isoformat()
                            })
        
        # List logs
        logs_dir = service_dir / "logs"
        if logs_dir.exists():
            for log_file in logs_dir.glob("*.log"):
                artifacts.append({
                    "name": log_file.name,
                    "path": str(log_file),
                    "run_id": None,
                    "url": f"/api/v1/services/{service_id}/artifacts/logs/{log_file.name}",
                    "size": log_file.stat().st_size,
                    "created_at": datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
                })
        
        return ApiResponse(
            success=True,
            message="Artifacts retrieved successfully",
            data=artifacts
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve artifacts: {str(e)}")
