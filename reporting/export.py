import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from datetime import datetime
import markdown
import webbrowser
from ..backtesting.metrics import calculate_metrics, calculate_advanced_metrics
from ..backtesting.visualization import create_equity_chart, create_drawdown_chart

class ReportGenerator:
    """Generate reports from backtest results."""
    
    def __init__(self, backtest_results):
        """
        Initialize the report generator.
        
        Parameters:
        -----------
        backtest_results : dict
            Dictionary containing backtest results
        """
        self.results = backtest_results
        self.metrics = calculate_advanced_metrics(backtest_results)
        
        # Extract key data
        self.equity = backtest_results['equity']
        self.trades = backtest_results.get('trades', pd.DataFrame())
        self.start_date = backtest_results.get('start_date', self.equity.index[0])
        self.end_date = backtest_results.get('end_date', self.equity.index[-1])
        
    def generate_report_content(self):
        """Generate the content for the report."""
        content = []
        
        # Title
        strategy_name = self.results.get('strategy_name', 'Strategy Backtest')
        content.append(f"# {strategy_name} Backtest Report")
        content.append(f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        content.append("")
        
        # Summary
        content.append("## Summary")
        content.append(f"- **Backtest Period:** {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")
        content.append(f"- **Initial Capital:** ${self.results['initial_capital']:,.2f}")
        content.append(f"- **Final Capital:** ${self.results['final_capital']:,.2f}")
        content.append(f"- **Total Return:** {self.metrics['total_return']:.2%}")
        content.append(f"- **Annual Return:** {self.metrics['annual_return']:.2%}")
        content.append(f"- **Sharpe Ratio:** {self.metrics['sharpe_ratio']:.2f}")
        content.append(f"- **Max Drawdown:** {self.metrics['max_drawdown']:.2%}")
        content.append("")
        
        # Performance Metrics
        content.append("## Performance Metrics")
        content.append("| Metric | Value |")
        content.append("| ------ | ----- |")
        content.append(f"| Total Return | {self.metrics['total_return']:.2%} |")
        content.append(f"| Annual Return | {self.metrics['annual_return']:.2%} |")
        content.append(f"| Volatility | {self.metrics['volatility']:.2%} |")
        content.append(f"| Sharpe Ratio | {self.metrics['sharpe_ratio']:.2f} |")
        content.append(f"| Sortino Ratio | {self.metrics['sortino_ratio']:.2f} |")
        content.append(f"| Max Drawdown | {self.metrics['max_drawdown']:.2%} |")
        if 'beta' in self.metrics:
            content.append(f"| Beta | {self.metrics['beta']:.2f} |")
        if 'alpha' in self.metrics:
            content.append(f"| Alpha | {self.metrics['alpha']:.2%} |")
        content.append("")
        
        # Drawdown Analysis
        content.append("## Drawdown Analysis")
        content.append(f"- **Average Drawdown:** {self.metrics['avg_drawdown']:.2%}")
        content.append(f"- **Average Duration:** {self.metrics['avg_drawdown_duration']:.1f} trading days")
        content.append(f"- **Number of Drawdowns:** {self.metrics['num_drawdowns']}")
        content.append("")
        
        # Top Drawdowns
        if self.metrics['top_drawdowns']:
            content.append("### Top Drawdowns")
            content.append("| Rank | Depth | Start Date | End Date | Duration |")
            content.append("| ---- | ----- | ---------- | -------- | -------- |")
            for i, dd in enumerate(self.metrics['top_drawdowns'], 1):
                content.append(f"| {i} | {dd['depth']:.2%} | {dd['start'].date()} | {dd['end'].date()} | {dd['duration']} days |")
            content.append("")
        
        # Trade Analysis
        if not self.trades.empty:
            content.append("## Trade Analysis")
            num_trades = len(self.trades)
            
            # Simple way to count winning trades - should be improved based on P&L
            winning_trades = self.trades[self.trades['quantity'] > 0].shape[0]
            win_rate = winning_trades / num_trades if num_trades > 0 else 0
            
            content.append(f"- **Number of Trades:** {num_trades}")
            content.append(f"- **Win Rate:** {win_rate:.2%}")
            content.append("")
            
            # Sample of recent trades
            content.append("### Recent Trades")
            recent_trades = self.trades.tail(10)
            content.append("| Date | Symbol | Quantity | Price | Commission |")
            content.append("| ---- | ------ | -------- | ----- | ---------- |")
            for _, trade in recent_trades.iterrows():
                content.append(f"| {trade['date'].date()} | {trade['symbol']} | {trade['quantity']} | ${trade['price']:.2f} | ${trade['commission']:.2f} |")
            content.append("")
        
        # Monthly Returns
        content.append("## Monthly Returns")
        monthly_returns = self.equity.resample('M').last().pct_change().dropna()
        content.append("| Year | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec | YTD |")
        content.append("| ---- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        
        # Group by year
        yearly_data = {}
        for date, ret in monthly_returns.items():
            year = date.year
            month = date.month
            
            if year not in yearly_data:
                yearly_data[year] = [None] * 12
                
            yearly_data[year][month-1] = ret
        
        # Generate table rows
        for year, months in sorted(yearly_data.items()):
            row = [f"{year}"]
            ytd_return = 1.0
            
            for i, ret in enumerate(months):
                if ret is None:
                    row.append("")
                else:
                    row.append(f"{ret:.1%}")
                    ytd_return *= (1 + ret)
            
            # Calculate YTD return
            row.append(f"{ytd_return - 1:.1%}")
            content.append("| " + " | ".join(row) + " |")
        
        content.append("")
        
        return "\n".join(content)
    
    def to_markdown(self, output_path):
        """Generate a Markdown report."""
        content = self.generate_report_content()
        
        # Create figures directory
        fig_dir = os.path.join(os.path.dirname(output_path), "figures")
        os.makedirs(fig_dir, exist_ok=True)
        
        # Generate charts
        self._generate_charts(fig_dir)
        
        # Add chart references
        content += "\n## Charts\n\n"
        content += f"![Equity Curve]({os.path.join('figures', 'equity_curve.png')})\n\n"
        content += f"![Drawdown]({os.path.join('figures', 'drawdown.png')})\n\n"
        
        # Save to file
        with open(output_path, 'w') as f:
            f.write(content)
        
        return output_path
    
    def to_html(self, output_path):
        """Generate an HTML report."""
        md_content = self.generate_report_content()
        
        # Create figures directory
        fig_dir = os.path.join(os.path.dirname(output_path), "figures")
        os.makedirs(fig_dir, exist_ok=True)
        
        # Generate charts
        self._generate_charts(fig_dir)
        
        # Add chart references
        md_content += "\n## Charts\n\n"
        md_content += f"![Equity Curve]({os.path.join('figures', 'equity_curve.png')})\n\n"
        md_content += f"![Drawdown]({os.path.join('figures', 'drawdown.png')})\n\n"
        
        # Convert markdown to HTML
        html_content = markdown.markdown(md_content, extensions=['tables'])
        
        # Create HTML document
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Backtest Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; max-width: 1000px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #444; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
        th, td {{ padding: 8px; text-align: left; border: 1px solid #ddd; }}
        th {{ background-color: #f2f2f2; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        img {{ max-width: 100%; height: auto; }}
    </style>
</head>
<body>
    {html_content}
</body>
</html>
"""
        
        # Save to file
        with open(output_path, 'w') as f:
            f.write(html)
        
        return output_path
    

    def to_pdf(self, output_path):
        """Generate a PDF report."""
        # First create HTML report
        html_path = output_path.replace('.pdf', '.html')
        self.to_html(html_path)
        
        try:
            # Try to use weasyprint if available
            from weasyprint import HTML
            HTML(html_path).write_pdf(output_path)
            return output_path
        except ImportError:
            # Fallback method - open HTML in browser and suggest print to PDF
            print(f"PDF generation library not available. Opening HTML in browser instead.")
            print(f"Please use your browser's 'Print to PDF' functionality to save as PDF.")
            
            webbrowser.open('file://' + os.path.abspath(html_path))
            print(f"HTML report saved to: {html_path}")
            
            return html_path
    
    def _generate_charts(self, figures_dir):
        """Generate and save charts for the report."""
        # Equity chart
        fig = create_equity_chart(self.equity)
        fig.savefig(os.path.join(figures_dir, 'equity_curve.png'), dpi=300, bbox_inches='tight')
        plt.close(fig)
        
        # Drawdown chart
        fig = create_drawdown_chart(self.equity)
        fig.savefig(os.path.join(figures_dir, 'drawdown.png'), dpi=300, bbox_inches='tight')
        plt.close(fig)
        
        # Monthly returns heatmap
        monthly_returns = self.equity.resample('M').last().pct_change().dropna()
        if len(monthly_returns) > 3:  # Only create if we have enough data
            fig = plt.figure(figsize=(10, 6))
            years = sorted(monthly_returns.index.year.unique())
            months = range(1, 13)
            
            # Create a matrix of returns
            returns_matrix = pd.DataFrame(index=years, columns=months, dtype=float)
            
            for date, ret in monthly_returns.items():
                returns_matrix.loc[date.year, date.month] = ret
            
            sns.heatmap(returns_matrix, annot=True, fmt='.1%', cmap='RdYlGn',
                      cbar_kws={'label': 'Monthly Return'}, linewidths=0.5)
            
            plt.title('Monthly Returns Heatmap')
            plt.xlabel('Month')
            plt.ylabel('Year')
            
            fig.savefig(os.path.join(figures_dir, 'monthly_returns.png'), dpi=300, bbox_inches='tight')
            plt.close(fig)

# algosystem/reporting/templates.py
class ReportTemplate:
    """Base class for report templates."""
    
    def __init__(self, title="Backtest Report"):
        """Initialize the report template."""
        self.title = title
        self.sections = []
    
    def add_section(self, title, content):
        """Add a section to the report."""
        self.sections.append({
            'title': title,
            'content': content
        })
    
    def generate(self):
        """Generate the report content."""
        raise NotImplementedError("Subclasses must implement this method")

class MarkdownTemplate(ReportTemplate):
    """Markdown report template."""
    
    def generate(self):
        """Generate markdown report content."""
        content = [f"# {self.title}", ""]
        
        for section in self.sections:
            content.append(f"## {section['title']}")
            content.append("")
            content.append(section['content'])
            content.append("")
        
        return "\n".join(content)

class HTMLTemplate(ReportTemplate):
    """HTML report template."""
    
    def generate(self):
        """Generate HTML report content."""
        sections_html = ""
        
        for section in self.sections:
            sections_html += f"<h2>{section['title']}</h2>\n"
            sections_html += f"<div>{section['content']}</div>\n"
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; max-width: 1000px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #444; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
        th, td {{ padding: 8px; text-align: left; border: 1px solid #ddd; }}
        th {{ background-color: #f2f2f2; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        img {{ max-width: 100%; height: auto; }}
    </style>
</head>
<body>
    <h1>{self.title}</h1>
    {sections_html}
</body>
</html>
"""
        return html

# Example usage of templates:
def create_strategy_report(backtest_results, template_type='markdown'):
    """Create a strategy report using templates."""
    from ..backtesting.metrics import calculate_advanced_metrics
    
    # Calculate metrics
    metrics = calculate_advanced_metrics(backtest_results)
    
    # Create appropriate template
    if template_type.lower() == 'html':
        template = HTMLTemplate(title=f"Strategy Backtest Report")
    else:
        template = MarkdownTemplate(title=f"Strategy Backtest Report")
    
    # Summary section
    summary = f"""
- **Period:** {backtest_results['start_date']} to {backtest_results['end_date']}
- **Initial Capital:** ${backtest_results['initial_capital']:,.2f}
- **Final Capital:** ${backtest_results['final_capital']:,.2f}
- **Total Return:** {metrics['total_return']:.2%}
- **Sharpe Ratio:** {metrics['sharpe_ratio']:.2f}
"""
    template.add_section("Summary", summary)
    
    # Performance metrics
    metrics_content = """
| Metric | Value |
|--------|-------|
"""
    for key, value in metrics.items():
        if isinstance(value, float):
            if 'return' in key or 'drawdown' in key:
                formatted_value = f"{value:.2%}"
            else:
                formatted_value = f"{value:.2f}"
            metrics_content += f"| {key.replace('_', ' ').title()} | {formatted_value} |\n"
    
    template.add_section("Performance Metrics", metrics_content)
    
    # Generate the report
    return template.generate()