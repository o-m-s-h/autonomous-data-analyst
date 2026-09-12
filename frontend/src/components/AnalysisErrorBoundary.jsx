import { Component } from "react";

export default class AnalysisErrorBoundary extends Component {
    state = { failed: false };

    static getDerivedStateFromError() {
        return { failed: true };
    }

    componentDidCatch(error, info) {
        console.error("Could not display the analysis", error, info.componentStack);
    }

    render() {
        if (this.state.failed) {
            return (
                <section role="alert">
                    <p>The analysis response could not be displayed. Please try asking again.</p>
                    <button onClick={this.props.onDismiss}>Dismiss</button>
                </section>
            );
        }
        return this.props.children;
    }
}
