import {
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
 * 10-minute bins from results/abbey/64 and 68, clipped to osm2pgsql overall.
 * Darwin powermetrics Combined_Power_mW; iostat disk0 total MB/s (no R/W split).
 * Index/cluster: 64 at 22:56:13 (328 min); 68 at 11:09:39 (361 min).
 */
const MINUTES = [
  0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160,
  170, 180, 190, 200, 210, 220, 230, 240, 250, 260, 270, 280, 290, 300, 310,
  320, 330, 340, 350, 360, 370, 380, 390, 400, 410, 420, 430, 440,
];

const FAST_W = [
  12.2, 10.3, 10.4, 9.8, 9.0, 9.8, 9.3, 10.0, 10.0, 10.0, 9.6, 10.1, 9.7, 10.2,
  9.8, 11.1, 9.7, 9.9, 5.4, 5.3, 4.6, 4.7, 4.8, 5.1, 4.8, 4.9, 5.2, 4.5, 4.7,
  4.9, 4.9, 4.8, 6.1, 7.7, 15.8, 26.0, 23.4, 23.4, 21.6, 16.7, 14.7, 18.5, 18.9,
  11.5, 2.8,
];

const DURABLE_W = [
  11.7, 9.7, 10.2, 9.6, 9.0, 9.5, 9.6, 9.5, 9.9, 9.7, 9.8, 9.8, 9.8, 10.1, 9.8,
  9.8, 9.6, 9.8, 7.5, 4.1, 4.6, 4.6, 4.4, 4.4, 4.7, 4.5, 4.1, 4.6, 4.3, 3.4, 2.2,
  2.5, 3.6, 3.8, 3.8, 3.7, 6.6, 3.7, 2.0, 5.2, 3.2, 4.2, 11.8, 17.7, 17.4,
];

const DISK0_MEAN = [
  0.27, 0.16, 0.15, 0.24, 0.27, 0.16, 0.34, 0.18, 0.3, 0.15, 0.28, 0.14, 0.28,
  0.15, 0.26, 0.23, 0.26, 0.21, 0.21, 0.18, 0.19, 0.17, 0.13, 0.15, 0.16, 0.15,
  0.15, 0.12, 0.13, 0.15, 0.14, 0.14, 0.51, 1.52, 1.25, 0.98, 0.97, 0.89, 1.16,
  0.73, 0.71, 0.24, 0.28, 0.22, 0.15,
];

const DISK0_PEAK = [
  3.38, 3.65, 1.94, 1.99, 1.51, 1.25, 1.71, 1.26, 2.03, 1.18, 1.67, 1.09, 1.73,
  1.42, 2.0, 1.36, 1.57, 1.71, 1.57, 0.75, 0.75, 0.85, 0.71, 0.55, 0.54, 0.67,
  0.71, 0.63, 0.69, 0.54, 0.53, 0.55, 3.32, 3.68, 3.67, 2.33, 2.46, 2.88, 3.69,
  3.68, 4.48, 3.19, 3.0, 3.88, 1.83,
];

export default function AbbeyM4MaxOsmPower() {
  const theme = useHostTheme();

  return (
    <Stack gap={20} style={{ padding: 24, maxWidth: 960 }}>
      <Stack gap={6}>
        <H1>Abbey M4 Max — OSM package power</H1>
        <Text tone="secondary" size="small">
          Source: results/abbey/64 (fast) and 68 (durable) · powermetrics
          Combined_Power_mW and Darwin iostat disk0 · 10-minute means and
          1-second peaks · PG18 · osm2pgsql-2.0 · 2026-10-14–16
        </Text>
      </Stack>

      <Grid columns={4} gap={12}>
        <Stat value="7.43 h" label="Fast 64" />
        <Stat value="11.10 h" label="Durable 68" tone="warning" />
        <Stat value="+49%" label="Time vs fast" tone="danger" />
        <Stat value="26 W" label="Index-bin mean (fast)" />
      </Grid>

      <Callout tone="danger">
        Same bundled fast→durable flip as Linux, much worse here: 7.45 h /
        404 kNodes/s vs 11.1 h / 270. Package draw never leaves the 20–40 W
        band. The penalty is time, not watts — Darwin fsync is the suspect,
        not WAL volume.
      </Callout>

      <Stack gap={8}>
        <H2>Combined power through 7.4 hours</H2>
        <Text tone="secondary" size="small">
          Minutes from osm2pgsql start · 10-minute mean of Combined_Power_mW
          / 1000. Fast index/cluster starts at 328 min; durable overlay is
          truncated at 440 min (that cell continues to 11.1 h).
        </Text>
        <LineChart
          categories={MINUTES.map((m) => `${m}`)}
          series={[
            { name: "Fast / minimal (64)", data: FAST_W, tone: "warning" },
            { name: "Durable / replica (68)", data: DURABLE_W, tone: "info" },
          ]}
          height={280}
          yMin={0}
          yMax={40}
          valueSuffix=" W"
          referenceLines={[
            { value: 10, label: "ingest cruise", tone: "neutral" },
            { value: 26, label: "fast index bin", tone: "warning" },
          ]}
        />
        <Text tone="secondary" size="small">
          X axis: minutes · Y axis: watts. Ingest is ~10 W, then ~5 W in
          ways, then the index window. Not a 9950X 180 W cliff.
        </Text>
      </Stack>

      <Stack gap={8}>
        <H2>disk0 throughput — same clock, fast 64</H2>
        <Text tone="secondary" size="small">
          Darwin iostat reports total MB/s (no read/write split) · 10-minute
          mean GB/s
        </Text>
        <LineChart
          categories={MINUTES.map((m) => `${m}`)}
          series={[{ name: "disk0 GB/s", data: DISK0_MEAN, tone: "warning" }]}
          height={240}
          yMin={0}
          yMax={1.8}
        />
        <Text tone="secondary" size="small">
          X axis: minutes · Y axis: GB/s. Ingest cruise ~0.2 GB/s. Index
          start (320–340 min) is ~1.5 GB/s mean.
        </Text>
      </Stack>

      <Stack gap={8}>
        <H2>Peak I/O in each period — 1-second samples</H2>
        <Text tone="secondary" size="small">
          Hottest single second in the same 10-minute bins · disk0 total ·
          test 64
        </Text>
        <LineChart
          categories={MINUTES.map((m) => `${m}`)}
          series={[{ name: "disk0 peak GB/s", data: DISK0_PEAK, tone: "info" }]}
          height={240}
          yMin={0}
          yMax={5}
        />
        <Text tone="secondary" size="small">
          X axis: minutes · Y axis: GB/s (1-second max). Peaks ~3.5–4.5 GB/s
          at index start. Averages never show it.
        </Text>
      </Stack>

      <Divider />

      <Card>
        <CardHeader>Why this is not siren’s thermal story</CardHeader>
        <CardBody>
          <Stack gap={8}>
            <Text>
              Mean Combined_Power is ~6 W over the clipped fast cell; the
              hottest 10-minute bin is 26 W. The Mac is not waiting on a board
              trip. It is waiting on durable I/O. Court (ARM Linux) paid ~12%
              for the same bundle; twilight ~6%. Abbey paid 49%. The PG19 2×2
              (wal_level vs fsync, FPW held on) is how to prove that.
            </Text>
            <Text tone="secondary" size="small">
              Test 64: fsync=off, wal_level=minimal, 7.43 h, 404 kNodes/s.
              Test 68: fsync=on, wal_level=replica, 11.10 h, 270 kNodes/s.
              Collectors kept sampling after overall on 64 — bins after 440
              min were dropped.
            </Text>
          </Stack>
        </CardBody>
      </Card>

      <Text tone="secondary" size="small" style={{ color: theme.text.secondary }}>
        Mac16,9 Studio · Homebrew PostgreSQL 18.6 · disk0 is the OSM volume
        in this iostat.
      </Text>
    </Stack>
  );
}
