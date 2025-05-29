"""Constraint display components for the API Testing Platform."""

import streamlit as st


def show_constraint(constraint):
    """Show an API constraint.

    Args:
        constraint: API constraint object (can be dict or Pydantic model)
    """
    # Check if constraint is a dictionary or a Pydantic model
    if isinstance(constraint, dict):
        constraint_type = constraint.get("type", "")
        description = constraint.get("description", "")
        severity = constraint.get("severity", "info")
        details = constraint.get("details", {})
    else:
        # It's a Pydantic model object
        constraint_type = getattr(constraint, "type", "")
        description = getattr(constraint, "description", "")
        severity = getattr(constraint, "severity", "info")
        details = getattr(constraint, "details", {})

    # Determine severity class for styling
    severity_class = {
        "info": "info-constraint",
        "warning": "warning-constraint",
        "error": "error-constraint",
    }.get(severity.lower(), "info-constraint")

    # Format the constraint type for display
    constraint_type_display = (
        constraint_type.replace("_", " ").title() if constraint_type else "General"
    )

    st.markdown(
        f"""
        <div class="constraint-item {severity_class}">
            <span class="constraint-type">{constraint_type_display}</span>
            <span class="constraint-severity">{severity.upper()}</span>
            <div class="constraint-description">{description}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Show constraint details if available
    if details:
        with st.expander("Constraint Details"):
            for key, value in details.items():
                st.markdown(f"**{key.replace('_', ' ').title()}:** {value}")


def show_constraints_section(constraints, title="API Constraints"):
    """Show a section of API constraints.

    Args:
        constraints: List of API constraints
        title: Section title
    """
    if not constraints:
        return

    st.markdown(f"#### {title}")

    # Group constraints by type
    constraint_by_type = {}
    for constraint in constraints:
        # Get the constraint type (handle both dict and object cases)
        if isinstance(constraint, dict):
            c_type = constraint.get("type", "general")
        else:
            c_type = getattr(constraint, "type", "general")

        if c_type not in constraint_by_type:
            constraint_by_type[c_type] = []
        constraint_by_type[c_type].append(constraint)

    # Show constraints by type
    for c_type, type_constraints in constraint_by_type.items():
        type_display = c_type.replace("_", " ").title() if c_type else "General"
        with st.expander(f"{type_display} Constraints ({len(type_constraints)})"):
            for constraint in type_constraints:
                show_constraint(constraint)
