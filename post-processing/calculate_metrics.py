import pandas as pd
import matplotlib.pyplot as plt

import seaborn as sns
import numpy as np

# Load power samples
df = pd.read_csv("isolated_inference_power_full.csv")


# Load inference durations
meta_df = pd.read_csv("per_frame_log_full.csv")
meta_df["inference_id"] = meta_df["Tag"].str.extract("(\d+)").astype(int) -1  # zero-indexed

# Sort data to ensure it's chronological
df = df.sort_values("Time_s").reset_index(drop=True)
meta_df = meta_df.sort_values("inference_id").reset_index(drop=True)

# Now assign inference IDs based on cumulative duration
start_time = df["Time_s"].iloc[0]
current_time = start_time
df["inference_id"] = -1  # Initialize all samples as unassigned
row_idx = 0

for i, row in meta_df.iterrows():
    duration = row["InferenceTime(s)"]
    end_time = current_time + duration
    
    # Assign samples within current time window to current inference_id
    mask = (df["Time_s"] >= current_time) & (df["Time_s"] < end_time)
    df.loc[mask, "inference_id"] = row["inference_id"]
    
    current_time = end_time

# Drop unassigned rows (if any)
df = df[df["inference_id"] != -1]

durations = meta_df.set_index("inference_id")["InferenceTime(s)"]


def compute_energy(group):
    inf_id = int(group.name)
    duration = durations.get(inf_id, 0.0)

    if len(group) == 0 or duration == 0.0:
        return pd.Series({"Mean_Power": 0.0, "Energy": 0.0})

    # Set negative values to 0 before squaring
    mean_power = group["Inference_Only"].clip(lower=0).mean()

    energy = mean_power * duration
    return pd.Series({"Mean_Power": mean_power, "Energy": energy})



results = df.groupby("inference_id").apply(compute_energy).reset_index()


# Mean energy
mean_energy_all = results["Energy"].mean()
print("Mean energy per inference (overall):", mean_energy_all)

# Plotting
plt.figure(figsize=(10, 5))
plt.plot(results["inference_id"], results["Energy"], marker='o', label="Energy per Inference")
plt.axhline(mean_energy_all, color='red', linestyle='--', label=f'Mean Energy = {mean_energy_all:.4f}')
plt.title("Energy per Inference")
plt.xlabel("Inference ID")
plt.ylabel("Energy (Joules)")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()

# Boxplot of Energy per Inference
# Calculate 5th and 95th percentiles
percentiles = np.percentile(results["Energy"], [5, 95])
lower, upper = percentiles

# Filter data between 5th and 95th percentiles
trimmed_data = results["Energy"][(results["Energy"] >= lower) & (results["Energy"] <= upper)]

# Create boxplot of trimmed data (showing middle 90% of values)
plt.figure(figsize=(6, 6))
sns.boxplot(data=trimmed_data, orient="v", color="skyblue", showmeans=True,
            meanprops={"marker": "o", "markerfacecolor": "red", "markeredgecolor": "black"},
            boxprops={"facecolor": "lightblue", "edgecolor": "blue"},
            medianprops={"color": "orange"})

plt.title("Energy per Inference (Trimmed to 5th–95th Percentile)")
plt.ylabel("Energy (Joules)")
plt.grid(True, axis='y')
plt.tight_layout()
plt.show()

# === Metrics Calculation ===

# Overall mean power per inference (mean of means)
overall_mean_power = results["Mean_Power"].mean()

# Mean Absolute Deviation (MEAD) of Power per Inference
mead_power = (results["Mean_Power"] - overall_mean_power).abs().mean()
print(f"MEAD Power/Inference (W): {mead_power:.4f}")


# Stdev of power per inference
std_power = results["Mean_Power"].std()

# Mean inference duration
mean_duration = durations.mean()

# Performance: inferences per second (total inferences / total time)
total_time = durations.sum()
performance_inf_per_s = len(durations) / total_time if total_time > 0 else 0.0

# Efficiency: performance per watt
mean_power_total = df["Inference_Only"].clip(lower=0).mean()
efficiency_perf_per_watt = performance_inf_per_s / mean_power_total if mean_power_total > 0 else 0.0

# === Print results ===
print(f"Overall Mean Power/Inference (W): {overall_mean_power:.4f}")
print(f"Standard Deviation of Power/Inference (W): {std_power:.4f}")
print(f"Mean Inference Duration (s): {mean_duration:.6f}")
print(f"Mean Energy Consumption/Inference (J): {mean_energy_all:.6f}")
print(f"Performance (inferences/s): {performance_inf_per_s:.4f}")
print(f"Efficiency (Perf per Watt): {efficiency_perf_per_watt:.4f}")



