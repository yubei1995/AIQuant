import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Set Chinese fonts for matplotlib
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

def generate_advanced_charts(df_block, output_dir, date_str):
    """
    Generate 4 subplots for top 20 blocks
    """
    # Sort by 1d return
    top_20 = df_block.sort_values('1d(%)', ascending=False).head(20)
    
    # Split into 4 groups
    groups = [
        top_20.iloc[0:5],   # 1-5
        top_20.iloc[5:10],  # 6-10
        top_20.iloc[10:15], # 11-15
        top_20.iloc[15:20]  # 16-20
    ]
    
    fig, axes = plt.subplots(4, 1, figsize=(15, 20))
    fig.suptitle(f'Top 20 Blocks Multi-Period Analysis - {date_str}', fontsize=16)
    
    periods = ['1d(%)', '3d(%)', '5d(%)', '10d(%)']
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    
    for i, ax in enumerate(axes):
        group_data = groups[i]
        if group_data.empty:
            ax.axis('off')
            continue
            
        # Prepare data for grouped bar chart
        x = np.arange(len(group_data))
        width = 0.2
        
        for j, period in enumerate(periods):
            vals = group_data[period].values
            rects = ax.bar(x + j*width, vals, width, label=period, color=colors[j])
            
            # Add labels
            for rect in rects:
                height = rect.get_height()
                ax.text(rect.get_x() + rect.get_width()/2., 1.01*height if height > 0 else height-0.5,
                        f'{height:.1f}',
                        ha='center', va='bottom' if height > 0 else 'top', fontsize=8)
        
        ax.set_ylabel('Return (%)')
        ax.set_title(f'Rank {i*5+1}-{i*5+5}')
        ax.set_xticks(x + width * 1.5)
        ax.set_xticklabels(group_data['细分板块'])
        ax.legend()
        ax.grid(axis='y', linestyle='--', alpha=0.3)
        
        # Add a horizontal line at 0
        ax.axhline(y=0, color='black', linewidth=0.8)

    plt.tight_layout(rect=[0, 0.03, 1, 0.97])
    chart_path = os.path.join(output_dir, "advanced_block_chart.png")
    plt.savefig(chart_path)
    plt.close()
    return chart_path
