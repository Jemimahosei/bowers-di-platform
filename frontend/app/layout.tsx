import type { Metadata } from "next";
import Header from "../components/Header";
import "./globals.css";

export const metadata: Metadata = {
  title: "Belonging at Bowers — Center for Belonging, Cornell Bowers CIS",
  description:
    "The Center for Belonging's tool to reach underrepresented students and get them using the Center's resources: resources, conferences, programs, newsletter, and appointments.",
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
              Center for Belonging — Cornell Bowers CIS Office of Diversity,
              Equity, Inclusion, and Belonging (DEIB). Director: Dr. LeeAnn
              Roberts. Associate Dean for Belonging: Hakim Weatherspoon.
            </p>
            <p>
              Contact:{" "}
              <a href="mailto:deib-office@bowers.cornell.edu">
                deib-office@bowers.cornell.edu
              </a>{" "}
              ·{" "}
              <a
                href="https://diversity.cis.cornell.edu"
                target="_blank"
                rel="noopener"
              >
                diversity.cis.cornell.edu
              </a>{" "}
              ·{" "}
              <a
                href="https://bowers.cornell.edu/belonging-bowers"
                target="_blank"
                rel="noopener"
              >
                Belonging at Bowers
              </a>
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
