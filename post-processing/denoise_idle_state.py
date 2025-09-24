import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.tsa.seasonal import STL

# === Load the CSV ===
df = pd.read_csv('idle_1ms.csv')

# Rename for easier access
df.columns = ['Time_s', 'Power_W']

# === Ensure it's sorted by time ===
df = df.sort_values('Time_s').reset_index(drop=True)

series = df['Power_W']


# ===  Apply STL decomposition ===
stl = STL(series, period= 7)  # Adjust `period` as needed
result = stl.fit()

df.plot(x='Time_s', y='Power_W', title='Power Over Time')
plt.xlabel('Time (s)')
plt.ylabel('Power (W)')
plt.show()



# === 5. Plot the components ===
result.plot()
plt.suptitle('STL Seasonal Decomposition of Power Data', fontsize=14)
plt.tight_layout()
plt.show()

cleaned = result.trend + result.seasonal

plt.figure(figsize=(12, 5))
plt.plot(df['Time_s'], series, label='Original', alpha=0.5)
plt.plot(df['Time_s'], cleaned, label='Denoised (Trend + Seasonal)', linewidth=2)
plt.xlabel('Time (s)')
plt.ylabel('Power (W)')
plt.title('Original vs Denoised Power')
plt.legend()
plt.show()

df['Denoised'] = result.trend + result.seasonal
# Create a new DataFrame with just Time and Denoised Power
denoised_df = df[['Time_s', 'Denoised']]

# Save to CSV
denoised_df.to_csv('denoised_power_idle_1ms.csv', index=False)
