import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "P&C Reserving Analytics",
  description: "Governed reserving analytics for actuarial teams"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

