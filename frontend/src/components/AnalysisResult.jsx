function AnalysisResult({ result }) {

    if (!result) {
        return null;
    }

    return (
        <div>

            <h2>Answer</h2>

            <p>
                {result.explanation}
            </p>


            <h3>SQL Query</h3>

            <pre>
                {result.sql}
            </pre>


            <h3>Result</h3>

            <table border="1">

                <thead>

                    <tr>

                        {result.result.length > 0 &&
                            Object.keys(
                                result.result[0]
                            ).map((column) => (
                                <th key={column}>
                                    {column}
                                </th>
                            ))
                        }

                    </tr>

                </thead>

                <tbody>

                    {result.result.map(
                        (row, index) => (

                            <tr key={index}>

                                {Object.values(row).map(
                                    (value, i) => (

                                        <td key={i}>
                                            {String(value)}
                                        </td>

                                    )
                                )}

                            </tr>

                        )
                    )}

                </tbody>

            </table>

        </div>
    );
}

export default AnalysisResult;