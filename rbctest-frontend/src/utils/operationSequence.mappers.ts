import type {
  OperationSequenceResponse,
  DependencyGraphResponse,
  OperationNode,
  DependencyEdge,
} from "@/types";

// Stable ID from operation string
function makeNodeId(operation: string): string {
  return `op:${operation}`; // deterministic
}

export function parseOperationStr(operation: string): {
  method: string;
  path: string;
} {
  const spaceIdx = operation.indexOf(" ");
  if (spaceIdx <= 0) return { method: "UNKNOWN", path: operation };
  return {
    method: operation.slice(0, spaceIdx),
    path: operation.slice(spaceIdx + 1),
  };
}

export function sequenceToDependencyGraph(
  sequence: OperationSequenceResponse
): DependencyGraphResponse {
  const seenOps = new Set<string>();
  const nodes: OperationNode[] = [];

  for (const op of sequence.operations) {
    if (seenOps.has(op)) continue;
    seenOps.add(op);
    const { method, path } = parseOperationStr(op);
    nodes.push({
      id: makeNodeId(op),
      operation: op,
      method,
      path,
      metadata: { from: "sequence", sequence_id: sequence.id },
    });
  }

  const edges: DependencyEdge[] = (sequence.dependencies || []).map(
    (dep, idx) => ({
      id: `e:${sequence.id}:${idx}`,
      source_node_id: makeNodeId(dep.source_operation),
      target_node_id: makeNodeId(dep.target_operation),
      dependency_type: "workflow",
      reason: dep.reason,
      data_mapping: dep.data_mapping || {},
      confidence: 0.9,
    })
  );

  return {
    nodes,
    edges,
    metadata: {
      sequence_id: sequence.id,
      sequence_type: sequence.sequence_type,
      operations_count: sequence.operations.length,
      dependencies_count: edges.length,
    },
  };
}

export function sequencesToDependencyGraph(
  sequences: OperationSequenceResponse[]
): DependencyGraphResponse {
  const nodeMap = new Map<string, OperationNode>();
  const edges: DependencyEdge[] = [];

  for (const seq of sequences) {
    for (const op of seq.operations) {
      const nodeId = makeNodeId(op);
      if (!nodeMap.has(nodeId)) {
        const { method, path } = parseOperationStr(op);
        nodeMap.set(nodeId, {
          id: nodeId,
          operation: op,
          method,
          path,
          metadata: { from: "sequences" },
        });
      }
    }

    for (const [idx, dep] of (seq.dependencies || []).entries()) {
      edges.push({
        id: `e:${seq.id}:${idx}`,
        source_node_id: makeNodeId(dep.source_operation),
        target_node_id: makeNodeId(dep.target_operation),
        dependency_type: "workflow",
        reason: dep.reason,
        data_mapping: dep.data_mapping || {},
        confidence: 0.8,
      });
    }
  }

  return {
    nodes: Array.from(nodeMap.values()),
    edges,
    metadata: {
      total_nodes: nodeMap.size,
      total_edges: edges.length,
      from: "sequences",
    },
  };
}
