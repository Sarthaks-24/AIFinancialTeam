import { useEffect, useState } from "react";
import { uploadFinancialFile } from "../../api/uploadApi";
import {
  Paper,
  Typography,
  TextField,
  Grid,
  Button,
  Box,
  CircularProgress,
  Alert,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from "@mui/material";
import { toast } from "react-toastify";

import {
  getFinancialData,
  getFinancialMonths,
  updateFinancialData,
} from "../../api/financeApi";

export default function FinanceData() {

  const [months, setMonths] = useState([]);
  const [selectedMonth, setSelectedMonth] = useState("");

  const [data, setData] = useState({
    month: "",
    revenue: "",
    expenses: "",
    ebitda: "",
    cash_position: "",
  });

  const [loadingMonth, setLoadingMonth] = useState(false);
  const [saving, setSaving] = useState(false);

  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");

  async function loadMonths() {
    const res = await getFinancialMonths();
    setMonths(res);

    if (res.length > 0) {
      setSelectedMonth((current) => current || res[0].month);
    }
  }

  useEffect(() => {
    loadMonths();
  }, []);

  useEffect(() => {
    if (!selectedMonth) return;

    async function fetchMonthData() {
      setLoadingMonth(true);
      try {
        const res = await getFinancialData(selectedMonth);
        setData(res);
      } catch {
        toast.error("Couldn't load data for that month.");
      } finally {
        setLoadingMonth(false);
      }
    }

    fetchMonthData();
  }, [selectedMonth]);

  function handleChange(e) {
    setData({
      ...data,
      [e.target.name]: e.target.value,
    });
  }

  function handleFileChange(event) {
    setSelectedFile(event.target.files[0]);
    setUploadError("");
  }

  async function handleUpload() {

    if (!selectedFile) {
      setUploadError("Please select a file first.");
      return;
    }

    setUploading(true);
    setUploadError("");

    try {
      const response = await uploadFinancialFile(selectedFile);

      toast.success(response.message || "File uploaded successfully");
      setSelectedFile(null);

      await loadMonths();

    } catch (error) {
      const backendMessage = error.response?.data?.error;
      setUploadError(backendMessage || "Upload failed. Please check your file and try again.");
    } finally {
      setUploading(false);
    }
  }

  async function handleSubmit() {
    setSaving(true);
    try {
      await updateFinancialData(data);
      toast.success(`Financial data for ${data.month} updated successfully`);
      await loadMonths();
    } catch {
      toast.error("Couldn't save changes. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Paper sx={{ p: { xs: 2.5, sm: 4 }, }}>

      <Typography variant="h4" mb={3}>
        Financial Data
      </Typography>

      <Box sx={{ mb: 4 }}>

        <Typography variant="h6" mb={2}>
          Upload Financial Statement
        </Typography>

        <input
          type="file"
          accept=".xlsx,.xls,.csv"
          onChange={handleFileChange}
          disabled={uploading}
        />

        {selectedFile && (
          <Typography sx={{ mt: 2, mb: 1 }}>
            Selected file: {selectedFile.name}
          </Typography>
        )}

        {uploadError && (
          <Alert severity="error" sx={{ mt: 1, mb: 2 }}>
            {uploadError}
          </Alert>
        )}

        <Button
          variant="contained"
          onClick={handleUpload}
          disabled={uploading || !selectedFile}
          startIcon={uploading ? <CircularProgress size={16} color="inherit" /> : null}
          sx={{ mt: 2 }}
        >
          {uploading ? "Uploading..." : "Upload File"}
        </Button>

      </Box>

      {months.length === 0 ? (
        <Alert severity="info">
          No financial data yet. Upload a file above to get started.
        </Alert>
      ) : (
        <>
          <Typography variant="h6" mb={2}>
            Edit a specific month
          </Typography>

          <FormControl size="small" sx={{ minWidth: 200, mb: 3 }}>
            <InputLabel>Month</InputLabel>
            <Select
              label="Month"
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(e.target.value)}
            >
              {months.map((m) => (
                <MenuItem key={m.id} value={m.month}>{m.month}</MenuItem>
              ))}
            </Select>
          </FormControl>

          {loadingMonth ? (
            <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
              <CircularProgress size={28} />
            </Box>
          ) : (
            <>
              <Grid container spacing={3}>

                <Grid size={{ xs: 12, md: 6 }}>
                  <TextField
                    fullWidth
                    label="Revenue"
                    name="revenue"
                    value={data.revenue}
                    onChange={handleChange}
                  />
                </Grid>

                <Grid size={{ xs: 12, md: 6 }}>
                  <TextField
                    fullWidth
                    label="Expenses"
                    name="expenses"
                    value={data.expenses}
                    onChange={handleChange}
                  />
                </Grid>

                <Grid size={{ xs: 12, md: 6 }}>
                  <TextField
                    fullWidth
                    label="EBITDA"
                    name="ebitda"
                    value={data.ebitda}
                    onChange={handleChange}
                  />
                </Grid>

                <Grid size={{ xs: 12, md: 6 }}>
                  <TextField
                    fullWidth
                    label="Cash Position"
                    name="cash_position"
                    value={data.cash_position}
                    onChange={handleChange}
                  />
                </Grid>

              </Grid>

              <Button
                variant="contained"
                sx={{ mt: 4 }}
                onClick={handleSubmit}
                disabled={saving}
                startIcon={saving ? <CircularProgress size={16} color="inherit" /> : null}
              >
                {saving ? "Saving..." : `Update ${data.month || "Financial Data"}`}
              </Button>
            </>
          )}
        </>
      )}

    </Paper>
  );
}
