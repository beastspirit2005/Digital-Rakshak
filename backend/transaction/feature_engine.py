import math
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import statistics


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle distance between two points on Earth in kilometers."""
    R = 6371.0  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (math.sin(dphi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


class FeatureEngine:
    """
    Computes deterministic fraud signals and statistical anomaly features 
    from a transaction and its contextual history.
    """

    def compute_features(
        self,
        current_txn: Dict[str, Any],
        account_history: Optional[List[Dict[str, Any]]] = None,
        beneficiary_profile: Optional[Dict[str, Any]] = None,
        device_profile: Optional[Dict[str, Any]] = None,
        user_baseline: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Calculates normalized features for a given transaction.
        
        :param current_txn: {amount, timestamp, account_id, beneficiary_id, device_id, latitude, longitude}
        :param account_history: List of past transactions for this account sorted by timestamp
        :param beneficiary_profile: Known profile of destination beneficiary
        :param device_profile: Known profile of device used
        :param user_baseline: Pre-aggregated behavioural baseline
        """
        features: Dict[str, float] = {}
        history = account_history or []
        
        amount = float(current_txn.get("amount", 0.0))
        txn_time = current_txn.get("timestamp")
        if isinstance(txn_time, str):
            txn_time = datetime.fromisoformat(txn_time.replace("Z", "+00:00"))
        elif not txn_time:
            txn_time = datetime.now(timezone.utc)

        # ------------------------------------------------------------------
        # 1. Amount Anomaly Features
        # ------------------------------------------------------------------
        past_amounts = [float(t["amount"]) for t in history if "amount" in t]
        
        if past_amounts:
            avg_amt = statistics.mean(past_amounts)
            med_amt = statistics.median(past_amounts)
            std_amt = statistics.stdev(past_amounts) if len(past_amounts) > 1 else 100.0
            std_amt = max(std_amt, 10.0)  # Avoid division by zero
            
            zscore = (amount - avg_amt) / std_amt
            ratio_to_avg = amount / max(avg_amt, 1.0)
            
            features["amount"] = amount
            features["avg_amount"] = avg_amt
            features["median_amount"] = med_amt
            features["amount_zscore"] = max(0.0, zscore)
            features["amount_ratio_to_avg"] = ratio_to_avg
            # Normalized amount anomaly score [0, 1]
            features["amount_anomaly_score"] = min(1.0, max(0.0, (amount - avg_amt) / (3.0 * std_amt))) if amount > avg_amt else 0.0
        else:
            # Cold start: Use default baseline or mild anomaly
            baseline_avg = float(user_baseline.get("avg_amount", 2500.0)) if user_baseline else 2500.0
            features["amount"] = amount
            features["avg_amount"] = baseline_avg
            features["median_amount"] = baseline_avg
            features["amount_zscore"] = 0.0
            features["amount_ratio_to_avg"] = amount / max(baseline_avg, 1.0)
            features["amount_anomaly_score"] = min(1.0, max(0.0, (amount - baseline_avg) / 10000.0)) if amount > baseline_avg else 0.0

        # Micro-probe test indicator (small amount e.g. <= 100 preceding a large spike)
        features["is_micro_probe"] = 1.0 if amount <= 100.0 else 0.0

        # ------------------------------------------------------------------
        # 2. Velocity Features (1m, 5m, 1h, 24h)
        # ------------------------------------------------------------------
        def get_count_and_vol_in_window(delta: timedelta):
            cutoff = txn_time - delta
            matching = [
                t for t in history 
                if (t.get("timestamp") if isinstance(t.get("timestamp"), datetime) else datetime.fromisoformat(str(t.get("timestamp")).replace("Z", "+00:00"))) >= cutoff
            ]
            return len(matching), sum(float(t.get("amount", 0.0)) for t in matching)

        c_1m, vol_1m = get_count_and_vol_in_window(timedelta(minutes=1))
        c_5m, vol_5m = get_count_and_vol_in_window(timedelta(minutes=5))
        c_1h, vol_1h = get_count_and_vol_in_window(timedelta(hours=1))
        c_24h, vol_24h = get_count_and_vol_in_window(timedelta(hours=24))

        features["txns_last_1m"] = float(c_1m)
        features["txns_last_5m"] = float(c_5m)
        features["txns_last_1h"] = float(c_1h)
        features["txns_last_24h"] = float(c_24h)
        features["amount_last_1h"] = vol_1h

        # Velocity Anomaly Score [0, 1]
        # Spike criteria: > 3 txns in 5 mins or > 8 in 1 hour
        vel_score = 0.0
        if c_1m >= 2:
            vel_score += 0.5
        if c_5m >= 4:
            vel_score += 0.3
        if c_1h >= 10:
            vel_score += 0.2
        features["velocity_anomaly_score"] = min(1.0, vel_score)

        # ------------------------------------------------------------------
        # 3. Beneficiary Features
        # ------------------------------------------------------------------
        curr_beneficiary = str(current_txn.get("beneficiary_id", "")).strip().lower()
        past_beneficiaries = {str(t.get("beneficiary_id", "")).strip().lower() for t in history if "beneficiary_id" in t}
        
        is_new_beneficiary = 1.0 if (curr_beneficiary and curr_beneficiary not in past_beneficiaries) else 0.0

        # Beneficiary age and risk
        b_age_hours = 720.0  # Default 30 days
        b_risk = 0.0
        b_prior_txns = 0.0

        if beneficiary_profile:
            b_risk = float(beneficiary_profile.get("risk_score", 0.0))
            if beneficiary_profile.get("is_flagged", False):
                b_risk = max(b_risk, 0.95)
            first_seen = beneficiary_profile.get("first_received_at")
            if first_seen:
                if isinstance(first_seen, str):
                    first_seen = datetime.fromisoformat(first_seen.replace("Z", "+00:00"))
                b_age_hours = max(0.1, (txn_time - first_seen).total_seconds() / 3600.0)
            b_prior_txns = float(beneficiary_profile.get("total_transactions", 0))
            # In fraud detection, any beneficiary registered within the last 24 hours is considered new
            if b_age_hours < 24.0:
                is_new_beneficiary = 1.0
        
        features["is_new_beneficiary"] = is_new_beneficiary
        features["beneficiary_age_hours"] = b_age_hours
        features["beneficiary_prior_txns"] = b_prior_txns
        features["beneficiary_risk_score"] = b_risk

        # New beneficiary sending high amount is a classic fraud vector
        if is_new_beneficiary == 1.0 and b_age_hours < 24.0:
            features["new_beneficiary_high_risk"] = 1.0
        else:
            features["new_beneficiary_high_risk"] = 0.0

        # ------------------------------------------------------------------
        # 4. Device Features
        # ------------------------------------------------------------------
        curr_device = str(current_txn.get("device_id", "")).strip()
        past_devices = {str(t.get("device_id", "")).strip() for t in history if t.get("device_id")}
        
        is_new_device = 1.0 if (curr_device and curr_device not in past_devices) else 0.0

        dev_account_count = 1.0
        dev_risk = 0.0
        dev_age_hours = 720.0
        if device_profile:
            dev_account_count = float(len(device_profile.get("associated_accounts", [1])))
            dev_risk = float(device_profile.get("risk_score", 0.0))
            if device_profile.get("is_emulator", False):
                dev_risk = max(dev_risk, 0.90)
                is_new_device = 1.0
            if dev_account_count >= 3:
                # Device shared across 3+ distinct accounts = strong fraud ring signal
                dev_risk = max(dev_risk, 0.85)
            first_seen_dev = device_profile.get("first_seen")
            if first_seen_dev:
                if isinstance(first_seen_dev, str):
                    first_seen_dev = datetime.fromisoformat(first_seen_dev.replace("Z", "+00:00"))
                dev_age_hours = max(0.1, (txn_time - first_seen_dev).total_seconds() / 3600.0)
                if dev_age_hours < 24.0:
                    is_new_device = 1.0

        features["is_new_device"] = is_new_device
        features["device_account_count"] = dev_account_count
        features["device_risk_score"] = dev_risk

        # ------------------------------------------------------------------
        # 5. Location Features
        # ------------------------------------------------------------------
        curr_lat = current_txn.get("latitude")
        curr_lon = current_txn.get("longitude")
        
        dist_km = 0.0
        if curr_lat is not None and curr_lon is not None:
            # Compare with last known transaction or typical centroid
            past_locations = [(t["latitude"], t["longitude"]) for t in history if t.get("latitude") and t.get("longitude")]
            if past_locations:
                last_lat, last_lon = past_locations[-1]
                dist_km = haversine_km(float(curr_lat), float(curr_lon), float(last_lat), float(last_lon))
            elif user_baseline and user_baseline.get("home_latitude") and user_baseline.get("home_longitude"):
                dist_km = haversine_km(float(curr_lat), float(curr_lon), float(user_baseline["home_latitude"]), float(user_baseline["home_longitude"]))
                
        features["distance_from_normal_km"] = dist_km
        features["location_anomaly_score"] = min(1.0, dist_km / 500.0) if dist_km > 50.0 else 0.0

        # ------------------------------------------------------------------
        # 6. Temporal Features
        # ------------------------------------------------------------------
        hour = txn_time.hour
        features["hour_of_day"] = float(hour)
        features["day_of_week"] = float(txn_time.weekday())
        
        # High risk hours in Indian banking: 01:00 AM - 05:00 AM (sleep time account takeover)
        is_unusual_hour = 1.0 if (1 <= hour <= 5) else 0.0
        features["is_unusual_hour"] = is_unusual_hour

        # Time elapsed since last txn
        if history and history[-1].get("timestamp"):
            last_time = history[-1]["timestamp"]
            if isinstance(last_time, str):
                last_time = datetime.fromisoformat(last_time.replace("Z", "+00:00"))
            time_diff_sec = max(0.0, (txn_time - last_time).total_seconds())
            features["time_since_last_txn_sec"] = time_diff_sec
        else:
            features["time_since_last_txn_sec"] = 86400.0  # default 1 day

        return features

