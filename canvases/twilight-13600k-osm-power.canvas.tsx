import {
  BarChart,
  Callout,
  Card,
  CardBody,
  CardHeader,
  Divider,
  Grid,
  H1,
  H2,
  LineChart,
  Stack,
  Stat,
  Text,
  useHostTheme,
} from "cursor/canvas";

/**
 * 10-minute bins from results/twilight/2595 (fast) and 2601 (durable).
 * turbostat PkgWatt; iostat nvme0n1. Index/cluster: 2595 at 16:05:42 (172 min);
 * 2601 at 08:14:39 (179 min).
 */
const MINUTES = [
  0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160,
  170, 180, 190, 200, 210, 220, 230, 240, 250, 260, 270, 280,
];

const FAST_AVG = [
  59.5, 46.3, 44.2, 45.9, 47.2, 49.6, 48.5, 48.1, 48.6, 48.3, 48.4, 43.5, 33.0,
  32.6, 32.6, 32.3, 32.6, 86.1, 95.7, 97.2, 63.5, 92.9, 40.3, 32.0, 31.7, 31.9,
  31.9, 32.1, 32.0,
];

const DURABLE_AVG = [
  59.6, 39.3, 42.0, 45.4, 45.8, 50.2, 50.2, 49.0, 49.0, 48.5, 48.2, 48.9, 32.6,
  32.4, 32.7, 32.1, 31.9, 33.6, 88.2, 94.0, 64.0, 68.5, 46.0, 45.9, 83.4, 32.8,
  31.9, 31.9, 31.8,
];

const NVME_READ_GB = [
  0, 0, 0, 0, 0.02, 0.04, 0.02, 0, 0, 0, 0.01, 0.05, 0.11, 0.1, 0.11, 0.1, 0.11,
  1.05, 0.72, 1.0, 0.16, 0.81, 0.05, 0.04, 0.04, 0.04, 0.04, 0.04, 0.04,
];

const NVME_WRITE_GB = [
  0.05, 0.09, 0.08, 0.16, 0.16, 0.17, 0.17, 0.11, 0.15, 0.16, 0.16, 0.14, 0.09,
  0.07, 0.07, 0.05, 0.05, 1.6, 0.68, 0.63, 0.21, 0.14, 0.06, 0.04, 0.02, 0.04,
  0.04, 0.04, 0.11,
];

const NVME_READ_PEAK = [
  0.23, 0.06, 0.04, 0.07, 0.11, 0.15, 0.19, 0.12, 0.05, 0.06, 0.59, 0.25, 0.17,
  0.23, 0.23, 0.22, 0.19, 4.82, 3.16, 8.62, 1.9, 8.64, 0.22, 0.06, 0.05, 0.06,
  0.05, 0.06, 0.07,
];

const NVME_WRITE_PEAK = [
  1.36, 1.85, 1.17, 6.49, 7.2, 7.1, 6.89, 7.03, 6.04, 6.83, 6.9, 6.99, 6.47,
  2.35, 2.21, 1.53, 1.3, 7.36, 4.34, 3.78, 4.3, 3.44, 4.26, 1.29, 1.29, 1.29,
  1.8, 1.46, 8.57,
];

const WATT_BANDS = [
  "20–40 W",
  "40–60 W",
  "60–80 W",
  "80–100 W",
  "100–140 W",
  "140–200 W",
];

export default function Twilight13600kOsmPower() {
  const theme = useHostTheme();

  return (
    <Stack gap={20} style={{ padding: 24, maxWidth: 960 }}>
      <Stack gap={6}>
        <H1>Twilight 13600K package power — OSM</H1>
        <Text tone="secondary" size="small">
          Source: results/twilight/2595 (fast) and 2601 (durable) · turbostat
          PkgWatt and iostat nvme0n1 · 10-minute means and 1-second peaks ·
          PG19 beta4 · set 118 · 2026-10-14–16
        </Text>
      </Stack>

      <Grid columns={4} gap={12}>
        <Stat value="49 W" label="Mean (fast 2595)" />
        <Stat value="45 W" label="Median" />
        <Stat value="149 W" label="1s peak PkgWatt" />
        <Stat value="+6%" label="Durable time vs fast" />
      </Grid>

      <Callout tone="info">
        Bundled durable costs ~15 minutes on this box (4.8 h / 626 kNodes/s
        vs 5.05 h / 593). Same cliff as siren at index start (~172 min),
        cooler package. Abbey paid +49% for the same GUC bundle.
      </Callout>

      <Stack gap={8}>
        <H2>Package watts through a 4.8-hour load</H2>
        <Text tone="secondary" size="small">
          Minutes from osm2pgsql start · 10-minute mean of PkgWatt. Index
          phase begins in the 170–180 minute bin. Durable overlay truncated
          at 280 min (cell 2601 runs to 5.11 h).
        </Text>
        <LineChart
          categories={MINUTES.map((m) => `${m}`)}
          series={[
            { name: "Fast / minimal (2595)", data: FAST_AVG, tone: "warning" },
            { name: "Durable / replica (2601)", data: DURABLE_AVG, tone: "info" },
          ]}
          height={280}
          yMin={0}
          yMax={160}
          valueSuffix=" W"
          referenceLines={[
            { value: 49, label: "fast mean", tone: "neutral" },
            { value: 97, label: "index bin", tone: "warning" },
          ]}
        />
        <Text tone="secondary" size="small">
          X axis: minutes · Y axis: package watts. Ingest cruise ~48 W, ways
          ~33 W, index ~95 W. Fast and durable traces sit on top of each
          other until the clock.
        </Text>
      </Stack>

      <Stack gap={8}>
        <H2>Disk I/O on nvme0n1 — same clock</H2>
        <Text tone="secondary" size="small">
          10-minute mean GB/s · test 2595 · index start lifts reads and
          writes together
        </Text>
        <LineChart
          categories={MINUTES.map((m) => `${m}`)}
          series={[
            { name: "Read GB/s", data: NVME_READ_GB, tone: "info" },
            { name: "Write GB/s", data: NVME_WRITE_GB, tone: "warning" },
          ]}
          height={260}
          yMin={0}
          yMax={1.8}
        />
        <Text tone="secondary" size="small">
          X axis: minutes · Y axis: GB/s. Ingest cruise is ~0.16 GB/s writes.
          Index start (170 min) is ~1.0 GB/s read and ~1.6 GB/s write.
        </Text>
      </Stack>

      <Stack gap={8}>
        <H2>Peak I/O in each period — 1-second samples</H2>
        <Text tone="secondary" size="small">
          Hottest single second in the same 10-minute bins · nvme0n1 · test
          2595
        </Text>
        <LineChart
          categories={MINUTES.map((m) => `${m}`)}
          series={[
            { name: "Read peak GB/s", data: NVME_READ_PEAK, tone: "info" },
            { name: "Write peak GB/s", data: NVME_WRITE_PEAK, tone: "warning" },
          ]}
          height={260}
          yMin={0}
          yMax={10}
        />
        <Text tone="secondary" size="small">
          X axis: minutes · Y axis: GB/s (1-second max). Same ~10 GB/s class
          as siren: 8.6 GB/s read, 8.6 GB/s write in a one-second sample.
          10-minute means never show it.
        </Text>
      </Stack>

      <Divider />

      <Stack gap={8}>
        <H2>Where the seconds go</H2>
        <Text tone="secondary" size="small">
          Share of 1-second PkgWatt samples in each band
        </Text>
        <BarChart
          categories={WATT_BANDS}
          series={[
            { name: "Fast 2595", data: [40.8, 40.4, 7.8, 5.1, 5.7, 0.2], tone: "warning" },
            { name: "Durable 2601", data: [40.8, 45.5, 7.4, 1.6, 4.2, 0.5], tone: "info" },
          ]}
          height={240}
          valueSuffix="%"
          yMax={50}
        />
        <Text tone="secondary" size="small">
          ~81% of a fast run sits in 20–60 W. The 80–140 W tail is the
          concurrent index window. Durable spends a bit more time in 40–60 W
          and less in 80–100 W — workers waiting on WAL.
        </Text>
      </Stack>

      <Card>
        <CardHeader>Linux vs Darwin on the same bundle</CardHeader>
        <CardBody>
          <Stack gap={8}>
            <Text>
              Twilight’s durable tax is a few percent on an already-fast
              13600K. Court’s Spark ARM cell was ~12%. Abbey’s M4 Max was
              49% and never drew enough watts for that to be thermal. WAL
              volume can still matter on some boxes; this one is not the Mac.
            </Text>
            <Text tone="secondary" size="small">
              Test 2595: fsync=off, wal_level=minimal, 4.77 h, 628 kNodes/s.
              Test 2601: fsync=on, wal_level=replica, 5.11 h, 586 kNodes/s.
              nvme0n1 is the Fury OSM disk.
            </Text>
          </Stack>
        </CardBody>
      </Card>

      <Text tone="secondary" size="small" style={{ color: theme.text.secondary }}>
        i5-13600K · 192 GB · Fury 4TB · PostgreSQL 19 beta4 · set 118.
      </Text>
    </Stack>
  );
}
