/* Hand-rolled SVG charts — no chart dependency. */

export function BarChart({
  data,
  labelKey,
  valueKey,
}: {
  data: Record<string, unknown>[];
  labelKey: string;
  valueKey: string;
}) {
  const width = 560;
  const barHeight = 26;
  const gap = 8;
  const labelWidth = 180;
  const height = data.length * (barHeight + gap) + 30;
  const max = Math.max(1, ...data.map((d) => Number(d[valueKey]) || 0));
  return (
    <svg
      width="100%"
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label="Bar chart"
      style={{ display: "block" }}
    >
      {data.map((d, i) => {
        const value = Number(d[valueKey]) || 0;
        const barW = ((width - labelWidth - 60) * value) / max;
        const y = i * (barHeight + gap);
        return (
          <g key={i}>
            <text x={0} y={y + 18} fontSize={12} fill="#2a2a2a">
              {String(d[labelKey]).slice(0, 28)}
            </text>
            <rect
              x={labelWidth}
              y={y}
              width={Math.max(barW, 2)}
              height={barHeight}
              fill="#b31b1b"
              rx={3}
            />
            <text
              x={labelWidth + Math.max(barW, 2) + 6}
              y={y + 18}
              fontSize={12}
              fill="#2a2a2a"
            >
              {value}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export function LineChart({
  data,
  labelKey,
  valueKey,
}: {
  data: Record<string, unknown>[];
  labelKey: string;
  valueKey: string;
}) {
  const width = 560;
  const height = 220;
  const pad = 36;
  const max = Math.max(1, ...data.map((d) => Number(d[valueKey]) || 0));
  const xs = (i: number) =>
    data.length <= 1
      ? width / 2
      : pad + (i * (width - pad * 2)) / (data.length - 1);
  const ys = (v: number) => height - pad - (v / max) * (height - pad * 2);
  const points = data
    .map((d, i) => `${xs(i)},${ys(Number(d[valueKey]) || 0)}`)
    .join(" ");
  return (
    <svg
      width="100%"
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label="Line chart"
      style={{ display: "block" }}
    >
      <line x1={pad} y1={height - pad} x2={width - pad} y2={height - pad} stroke="#dedede" />
      <line x1={pad} y1={pad} x2={pad} y2={height - pad} stroke="#dedede" />
      {data.length > 1 && (
        <polyline points={points} fill="none" stroke="#b31b1b" strokeWidth={2} />
      )}
      {data.map((d, i) => (
        <g key={i}>
          <circle
            cx={xs(i)}
            cy={ys(Number(d[valueKey]) || 0)}
            r={4}
            fill="#000056"
          />
          <text x={xs(i)} y={height - 12} fontSize={11} fill="#757575" textAnchor="middle">
            {String(d[labelKey])}
          </text>
          <text
            x={xs(i)}
            y={ys(Number(d[valueKey]) || 0) - 8}
            fontSize={11}
            fill="#2a2a2a"
            textAnchor="middle"
          >
            {Number(d[valueKey]) || 0}
          </text>
        </g>
      ))}
    </svg>
  );
}
