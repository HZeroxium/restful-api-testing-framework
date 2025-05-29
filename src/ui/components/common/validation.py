"""Validation display components for the API Testing Platform."""

import streamlit as st
from .badges import render_status_badge


def show_validation_result(validation):
    """Show a validation result.

    Args:
        validation: Validation result object (can be dict or Pydantic model)
    """
    # Check if validation is a dictionary or a Pydantic model
    if isinstance(validation, dict):
        status = validation["status"].lower()
        script_name = validation["script_name"]
        message = validation.get("message", "")
    else:
        # It's a Pydantic model object
        status = validation.status.lower()
        script_name = validation.script_name
        message = validation.message if validation.message else ""

    status_class = {
        "pass": "validation-pass",
        "fail": "validation-fail",
        "error": "validation-error",
    }.get(status, "")

    st.markdown(
        f"""
    <div class="validation-item {status_class}">
        {render_status_badge(status.upper())}
        <strong>{script_name}</strong>
        {': ' + message if message else ''}
    </div>
    """,
        unsafe_allow_html=True,
    )


def show_validation_script_details(validation, use_expander=True):
    """Show detailed validation script info with code in a dropdown.

    Args:
        validation: Validation result or script object (can be dict or Pydantic model)
        use_expander: Whether to use an expander for the validation code
    """
    # Check if validation is a dictionary or a Pydantic model
    if isinstance(validation, dict):
        script_name = validation.get("script_name", "")
        script_type = validation.get("script_type", "")
        status = validation.get("status", "").lower()
        validation_code = validation.get("validation_code", "")
        message = validation.get("message", "")
        script_id = validation.get("script_id", "")
    else:
        # It's a Pydantic model object
        script_name = getattr(validation, "script_name", "") or getattr(
            validation, "name", ""
        )
        script_type = getattr(validation, "script_type", "")
        status = (
            getattr(validation, "status", "").lower()
            if hasattr(validation, "status")
            else ""
        )
        validation_code = getattr(validation, "validation_code", "")
        message = getattr(validation, "message", "")
        script_id = getattr(validation, "script_id", "") or getattr(
            validation, "id", ""
        )

    # Create a status badge if status is available
    status_badge = ""
    if status:
        status_class = {
            "pass": "validation-pass",
            "fail": "validation-fail",
            "error": "validation-error",
        }.get(status, "")
        status_badge = render_status_badge(status.upper())

    # Display script info with or without an expander based on use_expander parameter
    if use_expander:
        with st.expander(f"{script_name} ({script_type or 'validation'})"):
            if message:
                st.markdown(f"**Message:** {message}")

            if validation_code:
                st.code(validation_code, language="python")
    else:
        # Display without an expander - enhanced visual styling for better clarity
        st.markdown(
            f"""<div style="background-color:#f8f9fa; padding:5px; border-left:3px solid #4b7bec; margin-bottom:10px;">
               <div style="font-weight:bold; margin-bottom:5px;">
                  {script_name} <span style="color:#666; font-size:0.9em;">({script_type or 'validation'})</span>
               </div>
            </div>""",
            unsafe_allow_html=True,
        )

        if message:
            st.markdown(f"**Message:** {message}")

        # Use a collapsible container with a toggle button instead of an expander
        if validation_code:
            # Create a truly unique key by combining script_id and script_name
            # If script_id is not available, use a random uuid
            if not script_id:
                import uuid

                script_id = str(uuid.uuid4())

            # Create a unique key that includes both id and name
            unique_key = f"code_{script_id}_{script_name}"
            show_code = st.checkbox(f"Show code", key=f"toggle_{unique_key}")
            if show_code:
                st.code(validation_code, language="python")
