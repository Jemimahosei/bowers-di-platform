import type { Metadata } from "next";
import Header from "../components/Header";
import "./globals.css";

export const metadata: Metadata = {
  title: "Open Door — Center for Belonging, Cornell Bowers CIS",
  description:
    "Open Door is the newsletter from the Center for Belonging at Cornell Bowers CIS. Each issue lists the conferences, funding, programs and support open to Bowers students right now, with the deadline next to each one.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Header />
        <main>{children}</main>
        <footer className="footer">
          <div className="footer-inner">
            <p>
              Open Door is a project of the Center for Belonging, Cornell
              Bowers CIS.
            </p>
            <p>
              Questions:{" "}
              <a href="mailto:deib-office@bowers.cornell.edu">
                deib-office@bowers.cornell.edu
              </a>
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
