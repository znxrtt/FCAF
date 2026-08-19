# FCAF: Framework for Cryptographic Agility Assessment

**FCAF (Framework for Cryptographic Agility Assessment)** is a comprehensive security tool designed to analyze, assess, and benchmark the cryptographic posture of modern applications and infrastructure. It evaluates readiness for Post-Quantum Cryptography (PQC), maps Cryptographic Bill of Materials (CBOM), and simulates real-world payment/PKI environments.

---

## 🚀 Key Features

- **CBOM Ingestion & Parsing:** Parses and structures cryptographic assets from network scanning, static evidence, and Cryptolyzer reports.
- **Cryptographic Maturity Engine:** Evaluates algorithms, key sizes, protocols, and agility metrics against modern standards (NIST PQC, PCI-DSS).
- **Impact Chain Analysis:** Identifies vulnerable cryptographic dependencies and visualizes the cascading blast radius across services.
- **Real-World Payment & PKI Simulation:** Simulates key rotation, tokenization, transaction signing, and Open Banking workflows under agile crypto configurations.
- **Interactive UI & Reporting:** Built with Streamlit for intuitive dashboards and exports detailed JSON/CSV assessment reports.

---

## 📂 Project Structure

```text
crypto-agility-review/
├── app.py                     # Streamlit web application & dashboard
├── main.py                    # Core CLI entry point
├── maturity_engine.py         # Scoring & crypto-agility calculation logic
├── rules.py                   # Cryptographic compliance & risk rule definitions
├── parsers.py                 # Multi-source parsers for CBOM and evidence
├── cryptolyzer_parser.py      # Parser for TLS/SSL & Cryptolyzer evidence
├── impact_chain.py            # Blast radius and dependency analyzer
├── recommendation_engine.py   # Remediation & migration path generator
├── report_generator.py        # Assessment summary and compliance reporting
├── payment_simulation/        # Mock environment for PKI, CA, and Payment Gateway
│   ├── certificate_authority/ # CA lifecycle & mTLS management
│   ├── open_banking/          # OAuth & token handling simulation
│   ├── payment_gateway/       # Transaction signing & verification
│   └── pki/                   # Key rotation & management services
└── tests/                     # Unit & integration test suite