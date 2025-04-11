import click
import yaml
import pandas as pd
import os
import pickle
import sys
from datetime import datetime
from ..backtesting import Engine
from ..data.connectors import database
from ..reporting import export
from ..utils import config

@click.group()
@click.version_option()
def cli():
    """AlgoSystem command line interface."""
    pass

@cli.command()
@click.option('--config', '-c', required=True, type=click.Path(exists=True),
              help='Path to the configuration file')
@click.option('--output', '-o', default=None,
              help='Path to save backtest results (pickle format)')
def backtest(config, output):
    """Run a backtest using the specified configuration file."""
    try:
        # Load configuration
        with open(config, 'r') as f:
            cfg = yaml.safe_load(f)
        
        click.echo(f"Loading configuration from {config}")
        
        # Load data
        data_path = cfg.get('data_path')
        if not data_path:
            click.echo("Error: data_path not specified in configuration", err=True)
            sys.exit(1)
            
        click.echo(f"Loading data from {data_path}")
        data = pd.read_csv(data_path, index_col=0, parse_dates=True)
        
        # Load strategy module
        strategy_path = cfg.get('strategy_path')
        strategy_name = cfg.get('strategy_name')
        
        if not strategy_path or not strategy_name:
            click.echo("Error: strategy_path and strategy_name must be specified", err=True)
            sys.exit(1)
        
        click.echo(f"Loading strategy {strategy_name} from {strategy_path}")
        
        # Add strategy directory to path and import
        sys.path.insert(0, os.path.dirname(strategy_path))
        strategy_module = __import__(os.path.basename(strategy_path).split('.')[0])
        strategy = getattr(strategy_module, strategy_name)
        
        # Setup backtest parameters
        params = cfg.get('parameters', {})
        start_date = params.get('start_date')
        end_date = params.get('end_date')
        initial_capital = params.get('initial_capital', 100000.0)
        commission = params.get('commission', 0.001)
        
        # Create and run backtest
        click.echo(f"Running backtest from {start_date} to {end_date}")
        engine = Engine(
            strategy=strategy,
            data=data,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            commission=commission
        )
        
        results = engine.run()
        
        # Display basic results
        click.echo(f"Backtest completed:")
        click.echo(f"  Initial capital: ${results['initial_capital']:,.2f}")
        click.echo(f"  Final capital:   ${results['final_capital']:,.2f}")
        click.echo(f"  Total return:    {results['returns']:.2%}")
        
        # Save results if output path specified
        if output:
            os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)
            with open(output, 'wb') as f:
                pickle.dump(results, f)
            click.echo(f"Results saved to {output}")
        
        # Optionally push to database
        if cfg.get('push_to_db', False):
            name = cfg.get('backtest_name', f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            description = cfg.get('description', '')
            strategy_type = cfg.get('strategy_type', '')
            
            click.echo(f"Pushing results to database as '{name}'")
            db_id = database.push_to_db(results, name, description, strategy_type)
            click.echo(f"Database ID: {db_id}")
        
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@cli.command()
@click.option('--results', '-r', required=True, type=click.Path(exists=True),
              help='Path to the results file (pickle format)')
@click.option('--name', '-n', required=True,
              help='Name for the backtest in the database')
@click.option('--description', '-d', default='',
              help='Description of the backtest')
@click.option('--strategy-type', '-s', default='',
              help='Type or category of the strategy')
def push(results, name, description, strategy_type):
    """Push backtest results to the database."""
    try:
        # Load results
        with open(results, 'rb') as f:
            results_data = pickle.load(f)
        
        # Push to database
        db_id = database.push_to_db(results_data, name, description, strategy_type)
        
        click.echo(f"Results successfully pushed to database with ID: {db_id}")
        
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@cli.command()
@click.option('--strategy-type', '-s', default=None,
              help='Filter by strategy type')
def list(strategy_type):
    """List backtests stored in the database."""
    try:
        # Get backtests from database
        backtests = database.list_from_db(strategy_type)
        
        if backtests.empty:
            click.echo("No backtests found in database")
            return
        
        # Display results
        click.echo("\nBacktests in database:")
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        
        # Format the output
        backtests['total_return'] = backtests['total_return'].apply(lambda x: f"{x:.2%}" if pd.notnull(x) else "N/A")
        backtests['sharpe_ratio'] = backtests['sharpe_ratio'].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else "N/A")
        backtests['max_drawdown'] = backtests['max_drawdown'].apply(lambda x: f"{x:.2%}" if pd.notnull(x) else "N/A")
        
        click.echo(backtests)
        
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)
            
@cli.command()
@click.option('--results', '-r', type=click.Path(exists=True),
              help='Path to the results file (pickle format)')
@click.option('--db-id', '-i', type=int, default=None,
              help='Database ID of the backtest')
@click.option('--db-name', '-n', default=None,
              help='Name of the backtest in the database')
@click.option('--output', '-o', required=True,
              help='Path to save the report')
@click.option('--format', '-f', default='pdf', type=click.Choice(['pdf', 'html', 'md']),
              help='Report format (pdf, html, or md)')
def report(results, db_id, db_name, output, format):
    """Generate a report from backtest results."""
    try:
        # Load results (from file or database)
        if results:
            with open(results, 'rb') as f:
                results_data = pickle.load(f)
        elif db_id or db_name:
            results_data = database.get_from_db(db_id, db_name)
        else:
            click.echo("Error: Either results file or database ID/name must be provided", err=True)
            sys.exit(1)
            
        if results_data is None:
            click.echo("Error: Could not load backtest results", err=True)
            sys.exit(1)
        
        # Generate report
        click.echo(f"Generating {format.upper()} report...")
        report_generator = export.ReportGenerator(results_data)
        
        if format == 'pdf':
            report_generator.to_pdf(output)
        elif format == 'html':
            report_generator.to_html(output)
        elif format == 'md':
            report_generator.to_markdown(output)
            
        click.echo(f"Report saved to {output}")
        
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@cli.command()
@click.option('--results', '-r', type=click.Path(exists=True),
              help='Path to the results file (pickle format)')
@click.option('--db-id', '-i', type=int, default=None,
              help='Database ID of the backtest')
@click.option('--db-name', '-n', default=None,
              help='Name of the backtest in the database')
def analyze(results, db_id, db_name):
    """Analyze backtest results and display metrics."""
    try:
        # Load results (from file or database)
        if results:
            with open(results, 'rb') as f:
                results_data = pickle.load(f)
        elif db_id or db_name:
            results_data = database.get_from_db(db_id, db_name)
        else:
            click.echo("Error: Either results file or database ID/name must be provided", err=True)
            sys.exit(1)
            
        if results_data is None:
            click.echo("Error: Could not load backtest results", err=True)
            sys.exit(1)
        
        # Import needed modules
        from ..backtesting.metrics import calculate_advanced_metrics
        
        # Calculate metrics
        metrics = calculate_advanced_metrics(results_data)
        
        # Display metrics
        click.echo("\nBacktest Performance Metrics:")
        click.echo("=" * 40)
        click.echo(f"Total Return:      {metrics['total_return']:.2%}")
        click.echo(f"Annual Return:     {metrics['annual_return']:.2%}")
        click.echo(f"Volatility:        {metrics['volatility']:.2%}")
        click.echo(f"Sharpe Ratio:      {metrics['sharpe_ratio']:.2f}")
        click.echo(f"Sortino Ratio:     {metrics['sortino_ratio']:.2f}")
        click.echo(f"Max Drawdown:      {metrics['max_drawdown']:.2%}")
        
        # Display drawdown information
        click.echo("\nDrawdown Analysis:")
        click.echo("=" * 40)
        click.echo(f"Average Drawdown:  {metrics['avg_drawdown']:.2%}")
        click.echo(f"Avg. Duration:     {metrics['avg_drawdown_duration']:.1f} trading days")
        click.echo(f"Total Drawdowns:   {metrics['num_drawdowns']}")
        
        # Show top drawdowns
        if metrics['top_drawdowns']:
            click.echo("\nTop Drawdowns:")
            for i, dd in enumerate(metrics['top_drawdowns'], 1):
                click.echo(f"  {i}. {dd['depth']:.2%} ({dd['start'].date()} to {dd['end'].date()}, {dd['duration']} days)")
        
        # Trade statistics if available
        if 'trades' in results_data and not results_data['trades'].empty:
            trades = results_data['trades']
            num_trades = len(trades)
            winning_trades = trades[trades['quantity'] > 0].shape[0]  # Simplistic, should be based on P&L
            win_rate = winning_trades / num_trades if num_trades > 0 else 0
            
            click.echo("\nTrade Analysis:")
            click.echo("=" * 40)
            click.echo(f"Number of Trades: {num_trades}")
            click.echo(f"Win Rate:         {win_rate:.2%}")
            
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@cli.command()
@click.option('--results', '-r', type=click.Path(exists=True),
              help='Path to the results file (pickle format)')
@click.option('--db-id', '-i', type=int, default=None,
              help='Database ID of the backtest')
@click.option('--db-name', '-n', default=None,
              help='Name of the backtest in the database')
@click.option('--output', '-o', default=None,
              help='Path to save the chart (if not provided, displays the chart)')
def visualize(results, db_id, db_name, output):
    """Visualize backtest results with interactive charts."""
    try:
        # Load results (from file or database)
        if results:
            with open(results, 'rb') as f:
                results_data = pickle.load(f)
        elif db_id or db_name:
            results_data = database.get_from_db(db_id, db_name)
        else:
            click.echo("Error: Either results file or database ID/name must be provided", err=True)
            sys.exit(1)
            
        if results_data is None:
            click.echo("Error: Could not load backtest results", err=True)
            sys.exit(1)
        
        # Import visualization module
        from ..backtesting.visualization import create_performance_dashboard
        
        # Create and show/save visualization
        click.echo("Generating performance visualization...")
        dashboard = create_performance_dashboard(results_data)
        
        if output:
            dashboard.save(output)
            click.echo(f"Visualization saved to {output}")
        else:
            dashboard.show()
        
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

if __name__ == '__main__':
    cli()