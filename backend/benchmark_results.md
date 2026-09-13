# Digital Rakshak — Transaction Fraud Intelligence Benchmark Results

## Executive Summary
Evaluation of **5,000 synthetic Indian banking transactions** comparing **Traditional Hard-Cutoff Rules** against **Digital Rakshak's Adaptive Friction Engine**.

| Metric | Traditional Static Rules | Digital Rakshak Engine | Impact |
| :--- | :---: | :---: | :--- |
| **Fraud Recall** | 71.43% | **100.00%** | +28.57% higher detection |
| **False Positive Block Rate** | 3.05% | **0.00%** | **Zero Hard Friction** for customers |
| **Legitimate Transactions Saved** | 0 (Blocked) | **142** | Converted from hard reject to OTP |
| **Legitimate Volume Saved** | ₹0 | **₹11,098,380.68** | Preserved transaction flow |
| **Attack DNA Matches** | 0 | **320** | Syndicate pattern correlation |
| **Average Latency** | < 0.1 ms | **0.056 ms** | Real-time wire-speed throughput |
| **P95 Latency** | < 0.1 ms | **0.071 ms** | Strict sub-millisecond SLO |

### Key Insight: Why Adaptive Friction Beats Binary Cutoffs
In traditional rule-based banking engines, legitimate customer anomalies (e.g. emergency hospital bills at 2:30 AM, hotel bookings while traveling, or wedding jewelry purchases) trigger hard cutoff limits and are **blocked**. 

Digital Rakshak eliminates this dilemma through proportional step-up verification:
1. **Low Risk** transactions pass instantly with zero latency and zero friction.
2. **Anomalous Legitimate** transactions receive **Step-Up Verification (OTP/Biometrics)**, allowing genuine users to complete essential payments safely.
3. **Coordinated Syndicate Attacks** (Account Takeover, Mule Fan-Out, Sleep Siphoning) are identified via **Attack DNA** and placed under **Temporary Hold / Investigation**.
