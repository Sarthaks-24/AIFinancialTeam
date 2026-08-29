import { Card, CardContent, Typography } from "@mui/material";

export default function KPICard({
  title,
  value,
  icon,
  color = "#1976d2",
}) {
  return (
    <Card
      sx={{
        height: "100%",
      }}
    >
      <CardContent>
        <Typography color="text.secondary">
          {title}
        </Typography>

        <Typography
          variant="h4"
          fontWeight="bold"
          mt={2}
          color={color}
        >
          {value}
        </Typography>

        <div style={{ marginTop: 15 }}>
          {icon}
        </div>
      </CardContent>
    </Card>
  );
}