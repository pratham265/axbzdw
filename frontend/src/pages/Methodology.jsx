import { useApi } from '../api'
import { Card, Status } from '../components/ui'

export default function Methodology() {
  const { data, loading, error } = useApi('/meta')
  if (!data) return <Status loading={loading} error={error} />
  const c = data.completeness

  return (
    <>
      <Card title="Scope">
        <ul>
          <li>Purchase decisions made <b>{data.decision_period[0]} to {data.decision_period[1]}</b>, which means delivery days <b>{data.delivery_period[0]} to {data.delivery_period[1]}</b>.</li>
          <li>Actuals: {data.sources.actuals}.</li>
          <li>Forecasts: {data.sources.forecasts}.</li>
          <li>No other data sources are used.</li>
        </ul>
      </Card>

      <Card title="Which forecast is evaluated">
        <p>{data.cutoff_rule}</p>
        <p>
          Forecasts published on the delivery day itself are excluded. Using them would credit the forecast with
          information the trader did not have when buying (look-ahead bias). In January, the forecast in use
          at decision time was always the one published at <b>{data.decision_publish_times.join(', ')}</b> UTC on D-1.
        </p>
        <p>WINDFOR rows whose target hour is earlier than their publish time are dropped, because they are not forecasts.</p>
      </Card>

      <Card title="How actuals and forecasts are matched">
        <ul>
          <li>WINDFOR is hourly and FUELHH is half-hourly. The actual for an hour is the mean of its two settlement periods. An hour with a missing half is excluded, not filled in.</li>
          <li>Where a settlement period was published more than once, the latest value is used.</li>
          <li>Error = forecast − actual (MW). A positive error is a shortfall the team would have had to buy.</li>
        </ul>
      </Card>

      <Card title="Metrics">
        <ul>
          <li><b>MAE</b>: typical size of the hourly error. <b>RMSE</b>: weights large misses more heavily. <b>Bias</b>: average signed error.</li>
          <li><b>nMAE</b> = MAE / mean actual output. MAPE is not used because it blows up when wind output is close to zero.</li>
          <li><b>P10 / P90</b>: empirical error quantiles. The P90 error is how much extra power would have covered 90% of hours.</li>
          <li><b>Skill</b> = 1 − MAE<sub>model</sub> / MAE<sub>baseline</sub>.</li>
          <li><b>Naive baseline</b>: the last actual published before the cutoff, held flat for the whole delivery day.</li>
          <li><b>Bias-corrected forecast</b>: the decision forecast minus the mean error over delivery days D-7 to D-2. D-1 is left out because its last settlement period is only published at the cutoff. This uses only information available at decision time.</li>
          <li>Likely-range bands on the day view use January's P10/P90 error per forecast-level bucket. They are an in-sample illustration for the pilot, not a back-tested interval.</li>
        </ul>
      </Card>

      <Card title="Data completeness">
        <table>
          <tbody>
            <tr><td>Delivery hours in scope</td><td>{c.expected_hours}</td></tr>
            <tr><td>Hours with a decision forecast</td><td>{c.hours_with_forecast}</td></tr>
            <tr><td>Hours with a complete actual</td><td>{c.hours_with_actual}</td></tr>
            <tr><td>Hours compared</td><td>{c.hours_compared}</td></tr>
            <tr><td>Raw FUELHH WIND rows</td><td>{c.raw_actual_rows}</td></tr>
            <tr><td>Raw WINDFOR rows / publishes</td><td>{c.raw_forecast_rows} / {c.forecast_publishes}</td></tr>
          </tbody>
        </table>
      </Card>
    </>
  )
}
