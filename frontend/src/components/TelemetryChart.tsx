import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
  Customized,
} from "recharts";
import type { TelemetryPoint } from "../lib/dashboardTypes";

type TelemetryChartProps = {
  data: TelemetryPoint[];
};

type CustomizedProps = {
  xAxisMap?: Record<string, { scale: (value: string) => number; bandwidth?: () => number }>;
  offset?: { left: number; top: number; width: number; height: number };
  data?: TelemetryPoint[];
};

const renderAnomalyBands = (props: CustomizedProps) => {
  const xAxis = props.xAxisMap ? props.xAxisMap[Object.keys(props.xAxisMap)[0]] : null;
  const { offset, data } = props;
  if (!xAxis || !offset || !data) return null;

  return data.map((point) => {
    if (!point.isAnomaly) return null;
    const xValue = xAxis.scale(point.timestamp);
    if (Number.isNaN(xValue)) return null;
    const bandWidth = xAxis.bandwidth ? Math.max(8, xAxis.bandwidth()) : 10;
    const x = offset.left + xValue - bandWidth / 2;

    return (
      <rect
        key={`anomaly-${point.timestamp}`}
        x={x}
        y={offset.top}
        width={bandWidth}
        height={offset.height}
        fill="rgba(239, 68, 68, 0.2)"
      />
    );
  });
};

export function TelemetryChart({ data }: TelemetryChartProps) {
  return (
    <div className="rounded-2xl border border-primary/20 bg-surface p-5 shadow-lg">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-text-main">Telemetry Pulse</h2>
        <p className="text-xs text-text-muted">CPU vs Error Rate</p>
      </div>

      <div className="mt-4 h-[240px]">
        {data.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-text-muted">
            Waiting for telemetry feed...
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 10, right: 20, bottom: 0, left: -10 }}>
              <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="3 3" />
              <XAxis dataKey="timestamp" stroke="rgba(255,255,255,0.35)" tick={{ fontSize: 10 }} />
              <YAxis stroke="rgba(255,255,255,0.35)" tick={{ fontSize: 10 }} />
              <Tooltip
                contentStyle={{ backgroundColor: "#110a08", border: "1px solid #9B3922", color: "#fff" }}
                labelStyle={{ color: "#F3D6C7" }}
              />
              <Customized component={renderAnomalyBands} />
              <Line type="monotone" dataKey="cpu" stroke="#f59e0b" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="errorRate" stroke="#ef4444" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
