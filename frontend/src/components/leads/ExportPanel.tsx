"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { opportunitiesApi } from "@/lib/api";
import { Opportunity } from "@/lib/types";
import { formatCurrency, formatDate } from "@/lib/utils";
import {
  Download,
  FileSpreadsheet,
  FileText,
  Loader2,
  CheckCircle,
} from "lucide-react";

type ExportFormat = "csv" | "excel" | "pdf";

interface ExportOptions {
  format: ExportFormat;
  includeArchived: boolean;
  columns: string[];
}

const AVAILABLE_COLUMNS = [
  { id: "title", label: "Titre" },
  { id: "organization", label: "Organisation" },
  { id: "status", label: "Statut" },
  { id: "score", label: "Score" },
  { id: "budget_amount", label: "Budget" },
  { id: "deadline_at", label: "Deadline" },
  { id: "source_name", label: "Source" },
  { id: "location_city", label: "Ville" },
  { id: "location_region", label: "Région" },
  { id: "contact_email", label: "Email contact" },
  { id: "contact_phone", label: "Téléphone" },
  { id: "created_at", label: "Date création" },
];

function generateCSV(opportunities: Opportunity[], columns: string[]): string {
  const headers = columns.map(
    (col) => AVAILABLE_COLUMNS.find((c) => c.id === col)?.label || col
  );
  
  const rows = opportunities.map((opp) =>
    columns.map((col) => {
      const value = (opp as any)[col];
      if (value === null || value === undefined) return "";
      if (col === "budget_amount") return formatCurrency(value);
      if (col.includes("_at")) return formatDate(value);
      return String(value).replace(/"/g, '""');
    })
  );

  const csvContent = [
    headers.join(","),
    ...rows.map((row) => row.map((cell) => `"${cell}"`).join(",")),
  ].join("\n");

  return csvContent;
}

function downloadFile(content: string, filename: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function ExportPanel() {
  const [format, setFormat] = useState<ExportFormat>("csv");
  const [selectedColumns, setSelectedColumns] = useState<string[]>([
    "title",
    "organization",
    "status",
    "score",
    "budget_amount",
    "deadline_at",
  ]);
  const [isExporting, setIsExporting] = useState(false);
  const [exportSuccess, setExportSuccess] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["opportunities", "export"],
    queryFn: () => opportunitiesApi.getAll({ limit: 1000 }),
  });

  // Extract items from paginated response
  const opportunities = data?.items || [];

  const handleExport = async () => {
    setIsExporting(true);
    
    try {
      const timestamp = new Date().toISOString().slice(0, 10);
      
      if (format === "csv") {
        const csv = generateCSV(opportunities, selectedColumns);
        downloadFile(csv, `opportunities-${timestamp}.csv`, "text/csv;charset=utf-8;");
      } else if (format === "excel") {
        // For Excel, we generate CSV with BOM for proper UTF-8 encoding in Excel
        const csv = "\ufeff" + generateCSV(opportunities, selectedColumns);
        downloadFile(csv, `opportunities-${timestamp}.csv`, "text/csv;charset=utf-8;");
      } else if (format === "pdf") {
        // Generate HTML table and print to PDF
        const html = generatePDFContent(opportunities, selectedColumns);
        const printWindow = window.open("", "_blank");
        if (printWindow) {
          printWindow.document.write(html);
          printWindow.document.close();
          printWindow.print();
        }
      }
      
      setExportSuccess(true);
      setTimeout(() => setExportSuccess(false), 3000);
    } catch (error) {
      console.error("Export error:", error);
    } finally {
      setIsExporting(false);
    }
  };

  const toggleColumn = (columnId: string) => {
    setSelectedColumns((prev) =>
      prev.includes(columnId)
        ? prev.filter((c) => c !== columnId)
        : [...prev, columnId]
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Download className="h-5 w-5" />
          Exporter les opportunités
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Format selection */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Format d'export</label>
          <div className="flex gap-2">
            <Button
              variant={format === "csv" ? "default" : "outline"}
              onClick={() => setFormat("csv")}
              className="flex-1"
            >
              <FileSpreadsheet className="h-4 w-4 mr-2" />
              CSV
            </Button>
            <Button
              variant={format === "excel" ? "default" : "outline"}
              onClick={() => setFormat("excel")}
              className="flex-1"
            >
              <FileSpreadsheet className="h-4 w-4 mr-2" />
              Excel
            </Button>
            <Button
              variant={format === "pdf" ? "default" : "outline"}
              onClick={() => setFormat("pdf")}
              className="flex-1"
            >
              <FileText className="h-4 w-4 mr-2" />
              PDF
            </Button>
          </div>
        </div>

        {/* Column selection */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Colonnes à exporter</label>
          <div className="flex flex-wrap gap-2">
            {AVAILABLE_COLUMNS.map((column) => (
              <Badge
                key={column.id}
                variant={selectedColumns.includes(column.id) ? "default" : "outline"}
                className="cursor-pointer"
                onClick={() => toggleColumn(column.id)}
              >
                {column.label}
              </Badge>
            ))}
          </div>
        </div>

        {/* Preview */}
        <div className="space-y-2">
          <label className="text-sm font-medium">
            Aperçu ({opportunities.length} opportunités)
          </label>
          <div className="border rounded-lg overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  {selectedColumns.slice(0, 4).map((col) => (
                    <TableHead key={col}>
                      {AVAILABLE_COLUMNS.find((c) => c.id === col)?.label}
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {opportunities.slice(0, 3).map((opp: Opportunity) => (
                  <TableRow key={opp.id}>
                    {selectedColumns.slice(0, 4).map((col) => (
                      <TableCell key={col} className="max-w-[200px] truncate">
                        {col === "budget_amount"
                          ? formatCurrency((opp as any)[col])
                          : col.includes("_at")
                          ? formatDate((opp as any)[col])
                          : (opp as any)[col] || "-"}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          {opportunities.length > 3 && (
            <p className="text-sm text-muted-foreground text-center">
              ... et {opportunities.length - 3} autres opportunités
            </p>
          )}
        </div>

        {/* Export button */}
        <Button
          onClick={handleExport}
          disabled={isExporting || selectedColumns.length === 0}
          className="w-full"
        >
          {isExporting ? (
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          ) : exportSuccess ? (
            <CheckCircle className="h-4 w-4 mr-2 text-green-500" />
          ) : (
            <Download className="h-4 w-4 mr-2" />
          )}
          {exportSuccess
            ? "Exporté avec succès !"
            : `Exporter ${opportunities.length} opportunités`}
        </Button>
      </CardContent>
    </Card>
  );
}

function generatePDFContent(opportunities: Opportunity[], columns: string[]): string {
  const headers = columns.map(
    (col) => AVAILABLE_COLUMNS.find((c) => c.id === col)?.label || col
  );

  const rows = opportunities
    .map(
      (opp) => `
      <tr>
        ${columns
          .map((col) => {
            const value = (opp as any)[col];
            if (value === null || value === undefined) return "<td>-</td>";
            if (col === "budget_amount") return `<td>${formatCurrency(value)}</td>`;
            if (col.includes("_at")) return `<td>${formatDate(value)}</td>`;
            return `<td>${value}</td>`;
          })
          .join("")}
      </tr>
    `
    )
    .join("");

  return `
    <!DOCTYPE html>
    <html>
    <head>
      <title>Export Opportunités - ${new Date().toLocaleDateString("fr-FR")}</title>
      <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; margin-bottom: 20px; }
        table { width: 100%; border-collapse: collapse; font-size: 12px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4f46e5; color: white; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        .footer { margin-top: 20px; color: #666; font-size: 10px; }
      </style>
    </head>
    <body>
      <h1>Export des Opportunités</h1>
      <p>Généré le ${new Date().toLocaleDateString("fr-FR")} - ${opportunities.length} opportunités</p>
      <table>
        <thead>
          <tr>${headers.map((h) => `<th>${h}</th>`).join("")}</tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
      <div class="footer">
        Opportunities Radar - Export automatique
      </div>
    </body>
    </html>
  `;
}
