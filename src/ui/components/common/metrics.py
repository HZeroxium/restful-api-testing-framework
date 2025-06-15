"""Metrics visualization components for the API Testing Platform."""

import streamlit as st


def show_metrics_summary(
    total_tests, total_passed, total_failed, total_errors, success_rate
):
    """Show metrics summary in a card.

    Args:
        total_tests: Total number of tests
        total_passed: Number of passed tests
        total_failed: Number of failed tests
        total_errors: Number of tests with errors
        success_rate: Success rate percentage
    """
    st.markdown(
        """<div class="summary-card">
        <h3 style="margin-top: 0;">Test Summary</h3>
        <div class="metric-row">
            <div class="metric-card">
                <div class="metric-value">{}</div>
                <div class="metric-label">Total Tests</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" style="color: #28a745;">{}</div>
                <div class="metric-label">Passed</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" style="color: #dc3545;">{}</div>
                <div class="metric-label">Failed</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" style="color: #fd7e14;">{}</div>
                <div class="metric-label">Errors</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" style="color: {}">{:.1f}%</div>
                <div class="metric-label">Success Rate</div>
            </div>
        </div>
    </div>""".format(
            total_tests,
            total_passed,
            total_failed,
            total_errors,
            (
                "#28a745"
                if success_rate >= 80
                else "#fd7e14" if success_rate >= 50 else "#dc3545"
            ),
            success_rate,
        ),
        unsafe_allow_html=True,
    )
