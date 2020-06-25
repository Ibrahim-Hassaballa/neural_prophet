import numpy as np
import pandas as pd

try:
    from matplotlib import pyplot as plt
    from matplotlib.dates import (
        MonthLocator,
        num2date,
        AutoDateLocator,
        AutoDateFormatter,
    )
    from matplotlib.ticker import FuncFormatter

    from pandas.plotting import deregister_matplotlib_converters
    deregister_matplotlib_converters()
except ImportError:
    print('Importing matplotlib failed. Plotting will not work.')


def set_y_as_percent(ax):
    """Set y axis as percentage

    Args:
        ax (matplotlib axis):

    Returns:
        ax
    """
    yticks = 100 * ax.get_yticks()
    yticklabels = ['{0:.4g}%'.format(y) for y in yticks]
    ax.set_yticklabels(yticklabels)
    return ax


def plot(fcst, ax=None, xlabel='ds', ylabel='y', highlight_forecast=None, figsize=(10, 6)):
    """Plot the NeuralProphet forecast

    Args:
        fcst (pd.DataFrame):  output of m.predict.
        ax (matplotlib axes):  on which to plot.
        xlabel (str): label name on X-axis
        ylabel (str): label name on Y-axis
        highlight_forecast (int): i-th step ahead forecast to highlight.
        figsize (tuple): width, height in inches.

    Returns:
        A matplotlib figure.
    """
    if ax is None:
        fig = plt.figure(facecolor='w', figsize=figsize)
        ax = fig.add_subplot(111)
    else:
        fig = ax.get_figure()
    ds = fcst['ds'].dt.to_pydatetime()
    print(fcst.tail().to_string())
    yhat_col_names = [col_name for col_name in fcst.columns if 'yhat' in col_name]
    for i in range(len(yhat_col_names)):
        ax.plot(ds, fcst['yhat{}'.format(i + 1)], ls='-', c='#0072B2', alpha=0.2 + 2.0/(i+2.5))
        # Future Todo: use fill_between for all but highlight_forecast
        """
        col1 = 'yhat{}'.format(i+1)
        col2 = 'yhat{}'.format(i+2)
        no_na1 = fcst.copy()[col1].notnull().values
        no_na2 = fcst.copy()[col2].notnull().values
        no_na = [x1 and x2 for x1, x2 in zip(no_na1, no_na2)]
        fcst_na = fcst.copy()[no_na]
        fcst_na_t = fcst_na['ds'].dt.to_pydatetime()
        ax.fill_between(
            fcst_na_t,
            fcst_na[col1],
            fcst_na[col2],
            color='#0072B2', alpha=1.0/(i+1)
            )
        """
    if highlight_forecast is not None:
        ax.plot(ds, fcst['yhat{}'.format(highlight_forecast)], ls='-', c='b')
        ax.plot(ds, fcst['yhat{}'.format(highlight_forecast)], 'bx')

    ax.plot(ds, fcst['y'], 'k.')

    # Specify formatting to workaround matplotlib issue #12925
    locator = AutoDateLocator(interval_multiples=False)
    formatter = AutoDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)
    ax.grid(True, which='major', c='gray', ls='-', lw=1, alpha=0.2)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    fig.tight_layout()
    return fig


def plot_components(m, fcst, forecast_in_focus=None, figsize=None):
    """Plot the NeuralProphet forecast components.

    Args:
        m (NeuralProphet): fitted model.
        fcst (pd.DataFrame):  output of m.predict.
        forecast_in_focus (int): n-th step ahead forecast AR-coefficients to plot
        figsize (tuple): width, height in inches.

    Returns:
        A matplotlib figure.
    """
    # Identify components to be plotted
    # as dict, minimum: {plot_name, comp_name}
    components = [{'plot_name': 'Trend',
                   'comp_name': 'trend'}]

    # print(fcst.head().to_string())
    # Future TODO: Add Holidays
    # if m.train_holiday_names is not None and 'holidays' in fcst:
    #     components.append('holidays')

    ## Plot  seasonalities, if present
    if m.season_config is not None:
        for name in m.season_config.periods:
            if name in m.season_config.periods: # and name in fcst:
                components.append({'plot_name': '{} seasonality'.format(name),
                                   'comp_name': 'season_{}'.format(name)})

    if m.n_lags > 0:
        components.append({'plot_name': 'Auto-Regression',
                           'comp_name': 'ar',
                           'num_overplot': m.n_forecasts,
                           'bar': True})
        if forecast_in_focus is not None:
            components.append({'plot_name': 'AR Forecast {}'.format(forecast_in_focus),
                               'comp_name': 'ar{}'.format(forecast_in_focus)})

    # Add Covariates
    if m.covar_config is not None:
        for name in m.covar_config.keys():
            components.append({'plot_name': 'Covariate "{}"'.format(name),
                               'comp_name': 'covar_{}'.format(name),
                               'num_overplot': m.n_forecasts,
                               'bar': True})
            if forecast_in_focus is not None:
                components.append({'plot_name': 'COV "{}" Forecast {}'.format(name, forecast_in_focus),
                                   'comp_name': 'covar_{}{}'.format(name, forecast_in_focus)})
    if 'residuals' in fcst:
        components.append({'plot_name': 'Residuals',
                           'comp_name': 'residuals',
                           'rolling': 7,
                           'bar': True})

    npanel = len(components)
    figsize = figsize if figsize else (9, 3 * npanel)
    fig, axes = plt.subplots(npanel, 1, facecolor='w', figsize=figsize)
    if npanel == 1:
        axes = [axes]
    multiplicative_axes = []
    for ax, comp in zip(axes, components):
        name = comp['plot_name'].lower()
        if name in ['trend', 'residuals'] \
                or ('ar' in name and 'forecast' in name) \
                or ('cov' in name and 'forecast' in name):
            plot_forecast_component(fcst=fcst, ax=ax, **comp)
        elif 'season' in name:
            if m.season_config.mode == 'multiplicative':
                multiplicative_axes.append(ax)
            plot_forecast_component(fcst=fcst, ax=ax, **comp)
        elif 'auto-regression' in name or 'covariate' in name:
            plot_multiforecast_component(fcst=fcst, ax=ax, **comp)

    fig.tight_layout()
    # Reset multiplicative axes labels after tight_layout adjustment
    for ax in multiplicative_axes: ax = set_y_as_percent(ax)
    return fig


def plot_forecast_component(fcst, comp_name, plot_name=None, ax=None, figsize=(10, 6),
                            multiplicative=False, bar=False, rolling=None):
    """Plot a particular component of the forecast.

    Args:
        fcst (pd.DataFrame):  output of m.predict.
        comp_name (str): Name of the component to plot.
        plot_name (str): Name of the plot Title.
        ax (matplotlib axis): matplotlib Axes to plot on.
        figsize (tuple): width, height in inches.
        multiplicative (bool): set y axis as percentage
        bar (bool): make barplot
        rolling (int): rolling average underplot

    Returns:
        a list of matplotlib artists
    """
    artists = []
    if not ax:
        fig = plt.figure(facecolor='w', figsize=figsize)
        ax = fig.add_subplot(111)
    fcst_t = fcst['ds'].dt.to_pydatetime()
    if rolling is not None:
        rolling_avg = fcst[comp_name].rolling(rolling, min_periods=1, center=True).mean()
        if bar: artists += ax.bar(fcst_t, rolling_avg, width=1.00, color='#0072B2', alpha=0.5)
        else: artists += ax.plot(fcst_t, rolling_avg, ls='-', color='#0072B2', alpha=0.5)
    if bar: artists += ax.bar(fcst_t, fcst[comp_name], width=1.00, color='#0072B2')
    else: artists += ax.plot(fcst_t, fcst[comp_name], ls='-', c='#0072B2')
    # Specify formatting to workaround matplotlib issue #12925
    locator = AutoDateLocator(interval_multiples=False)
    formatter = AutoDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)
    ax.grid(True, which='major', c='gray', ls='-', lw=1, alpha=0.2)
    ax.set_xlabel('ds')
    if plot_name is None: plot_name = comp_name
    ax.set_ylabel(plot_name)
    if multiplicative: ax = set_y_as_percent(ax)
    return artists


def plot_multiforecast_component(fcst, comp_name, plot_name=None, ax=None, figsize=(10, 6),
                                 multiplicative=False, bar=False, focus=1, num_overplot=None):
    """Plot a particular component of the forecast.

    Args:
        fcst (pd.DataFrame):  output of m.predict.
        comp_name (str): Name of the component to plot.
        plot_name (str): Name of the plot Title.
        ax (matplotlib axis): matplotlib Axes to plot on.
        figsize (tuple): width, height in inches.
        multiplicative (bool): set y axis as percentage
        bar (bool): make barplot
        focus (int): forecast number to portray in detail.
        num_overplot (int): overplot all forecasts up to num
            None (default): only plot focus

    Returns:
        a list of matplotlib artists
    """
    artists = []
    if not ax:
        fig = plt.figure(facecolor='w', figsize=figsize)
        ax = fig.add_subplot(111)
    fcst_t = fcst['ds'].dt.to_pydatetime()
    col_names = [col_name for col_name in fcst.columns if col_name.startswith(comp_name)]
    assert num_overplot <= len(col_names)
    if num_overplot is not None:
        for i in list(range(num_overplot))[::-1]:
            y = fcst['{}{}'.format(comp_name, i+1)]
            notnull = y.notnull()
            alpha_min = 0.2
            alpha_softness = 1.2
            alpha = alpha_min + alpha_softness*(1.0-alpha_min) / (i + 1.0*alpha_softness)
            if bar:
                artists += ax.bar(fcst_t[notnull], y[notnull], width=1.00, color='#0072B2',  alpha=alpha)
            else:
                artists += ax.plot(fcst_t[notnull], y[notnull], ls='-', color='#0072B2',  alpha=alpha)
    if num_overplot is None or focus > 1:
        y = fcst['{}{}'.format(comp_name, focus)]
        notnull = y.notnull()
        if bar:
            artists += ax.bar(fcst_t[notnull], y[notnull], width=1.00, color='b')
        else:
            artists += ax.plot(fcst_t[notnull], y[notnull], ls='-', color='b')
    # Specify formatting to workaround matplotlib issue #12925
    locator = AutoDateLocator(interval_multiples=False)
    formatter = AutoDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)
    ax.grid(True, which='major', color='gray', ls='-', lw=1, alpha=0.2)
    ax.set_xlabel('ds')
    if plot_name is None: plot_name = comp_name
    ax.set_ylabel(plot_name)
    if multiplicative: ax = set_y_as_percent(ax)
    return artists


def plot_parameters(m, forecast_in_focus=None, weekly_start=0, yearly_start=0, figsize=None,):
    """Plot the parameters that the model is composed of, visually.

    Args:
        m (NeuralProphet): fitted model.
        forecast_in_focus (int): n-th step ahead forecast AR-coefficients to plot
        weekly_start (int):  specifying the start day of the weekly seasonality plot.
            0 (default) starts the week on Sunday.
            1 shifts by 1 day to Monday, and so on.
        yearly_start (int): specifying the start day of the yearly seasonality plot.
            0 (default) starts the year on Jan 1.
            1 shifts by 1 day to Jan 2, and so on.
        figsize (tuple): width, height in inches.

    Returns:
        A matplotlib figure.
    """
    # Identify components to be plotted
    # as dict: {plot_name, }
    components = []
    if m.n_changepoints > 0:
        components.append({'plot_name': 'Trend changepoints'})

    # Future TODO: Add Holidays

    ## Plot  seasonalities, if present
    if m.season_config is not None:
        for name in m.season_config.periods:
            components.append({'plot_name': 'seasonality', 'comp_name': name})

    if m.n_lags > 0:
        components.append({
            'plot_name': 'lagged weights',
            'comp_name': 'AR',
            'weights': m.model.ar_weights.detach().numpy(),
            'focus': None})
        if forecast_in_focus is not None:
            components.append({
                'plot_name': 'lagged weights',
                'comp_name': 'AR',
                'weights': m.model.ar_weights.detach().numpy(),
                'focus': forecast_in_focus})
    # Add Covariates
    if m.covar_config is not None:
        for name in m.covar_config.keys():
            components.append({
                'plot_name': 'lagged weights',
                'comp_name': 'COV "{}"'.format(name),
                'weights': m.model.get_covar_weights(name).detach().numpy(),
                'focus': None})
            if forecast_in_focus is not None:
                components.append({
                    'plot_name': 'lagged weights',
                    'comp_name': 'COV "{}"'.format(name),
                    'weights': m.model.get_covar_weights(name).detach().numpy(),
                    'focus': forecast_in_focus})

    if len(components) == 0:
        components.append({'plot_name': 'Trend'})
    npanel = len(components)
    figsize = figsize if figsize else (9, 3 * npanel)
    fig, axes = plt.subplots(npanel, 1, facecolor='w', figsize=figsize)
    if npanel == 1:
        axes = [axes]
    multiplicative_axes = []
    for ax, comp in zip(axes, components):
        plot_name = comp['plot_name'].lower()
        if plot_name.startswith('trend'):
            if 'changepoints' in plot_name:
                plot_trend_change(m=m, ax=ax, plot_name=comp['plot_name'])
            else:
                plot_trend_0(m=m, ax=ax,  plot_name=comp['plot_name'])
        elif plot_name.startswith('seasonality'):
            name = comp['comp_name']
            if m.season_config.mode == 'multiplicative':
                multiplicative_axes.append(ax)
            if name.lower() == 'weekly' or m.season_config.periods[name]['period'] == 7:
                plot_weekly(m=m, ax=ax, weekly_start=weekly_start, comp_name=name)
            elif name.lower() == 'yearly' or m.season_config.periods[name]['period'] == 365.25:
                plot_yearly(m=m, ax=ax, yearly_start=yearly_start, comp_name=name)
            else:
                plot_custom_season(m=m, ax=ax, comp_name=name)
        elif plot_name == 'lagged weights':
            plot_lagged_weights(weights=comp['weights'], comp_name=comp['comp_name'], focus=comp['focus'], ax=ax)
    fig.tight_layout()
    # Reset multiplicative axes labels after tight_layout adjustment
    for ax in multiplicative_axes: ax = set_y_as_percent(ax)
    return fig


def plot_trend_change(m, ax=None, plot_name='Trend Change', figsize=(10, 6)):
    """Make a barplot of the magnitudes of trend-changes.

    Args:
        m (NeuralProphet): fitted model.
        ax (matplotlib axis): matplotlib Axes to plot on.
            One will be created if this is not provided.
        plot_name (str): Name of the plot Title.
        figsize (tuple): width, height in inches.

    Returns:
        a list of matplotlib artists
    """
    artists = []
    if not ax:
        fig = plt.figure(facecolor='w', figsize=figsize)
        ax = fig.add_subplot(111)

    cp_range = range(0, 1 + m.n_changepoints)
    weights = m.model.get_trend_deltas.detach().numpy()
    artists += ax.bar(cp_range, weights, width=1.00, color='#0072B2')

    ax.grid(True, which='major', c='gray', ls='-', lw=1, alpha=0.2)
    ax.set_xlabel("Trend Segment")
    ax.set_ylabel(plot_name)
    return artists


def plot_trend_0(m, ax=None, plot_name='Trend', figsize=(10, 6)):
    """Make a barplot of the magnitudes of trend-changes.

    Args:
        m (NeuralProphet): fitted model.
        ax (matplotlib axis): matplotlib Axes to plot on.
            One will be created if this is not provided.
        plot_name (str): Name of the plot Title.
        figsize (tuple): width, height in inches.

    Returns:
        a list of matplotlib artists
    """
    artists = []
    if not ax:
        fig = plt.figure(facecolor='w', figsize=figsize)
        ax = fig.add_subplot(111)
    t_start = m.data_params['ds'].shift
    t_end = t_start + m.data_params['ds'].scale
    fcst_t = pd.Series([t_start, t_end]).dt.to_pydatetime()
    trend_0 = m.model.trend_m0.detach().numpy()
    trend_1 = trend_0 + m.model.trend_k0.detach().numpy()
    # trend_0 = trend_0 * m.data_params['y'].scale + m.data_params['y'].shift
    # trend_1 = trend_1 * m.data_params['y'].scale + m.data_params['y'].shift
    artists += ax.plot(fcst_t, [trend_0, trend_1], ls='-', c='#0072B2')

    # Specify formatting to workaround matplotlib issue #12925
    locator = AutoDateLocator(interval_multiples=False)
    formatter = AutoDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)
    ax.grid(True, which='major', c='gray', ls='-', lw=1, alpha=0.2)
    ax.set_xlabel('ds')
    ax.set_ylabel(plot_name)
    return artists


def plot_lagged_weights(weights, comp_name, focus=None, ax=None, figsize=(10, 6)):
    """Make a barplot of the importance of lagged inputs.

    Args:
        weights (np.array): model weights as matrix or vector
        comp_name (str): name of lagged inputs
        focus (int): if provided, show weights for this forecast
            None (default) sum over all forecasts and plot as relative percentage
        ax (matplotlib axis): matplotlib Axes to plot on.
            One will be created if this is not provided.
        figsize (tuple): width, height in inches.
    Returns:
        a list of matplotlib artists
    """
    artists = []
    if not ax:
        fig = plt.figure(facecolor='w', figsize=figsize)
        ax = fig.add_subplot(111)
    n_lags = weights.shape[0]
    lags_range = list(range(1, 1 + n_lags))[::-1]
    if focus is None:
        weights = np.sum(np.abs(weights), axis=0)
        weights = weights / np.sum(weights)
        artists += ax.bar(lags_range, weights, width=1.00, color='#0072B2')
    else:
        if len(weights.shape) == 2:
            weights = weights[focus-1, :]
        artists += ax.bar(lags_range, weights, width=0.80, color='#0072B2')
    ax.grid(True, which='major', c='gray', ls='-', lw=1, alpha=0.2)
    ax.set_xlabel("{} lag number".format(comp_name))
    if focus is None:
        ax.set_ylabel('{} relevance'.format(comp_name))
        ax = set_y_as_percent(ax)
    else:
        ax.set_ylabel('{} weight ({})-ahead'.format(comp_name, focus))
    return artists


def plot_custom_season(m, ax=None, comp_name=None):
    raise NotImplementedError


def plot_yearly(m, ax=None, yearly_start=0, figsize=(10, 6), comp_name='yearly'):
    """Plot the yearly component of the forecast.

    Args:
        m (NeuralProphet): fitted model.
        ax (matplotlib axis): matplotlib Axes to plot on.
            One will be created if this is not provided.
        yearly_start (int): specifying the start day of the yearly seasonality plot.
            0 (default) starts the year on Jan 1.
            1 shifts by 1 day to Jan 2, and so on.
        figsize (tuple): width, height in inches.
        comp_name (str): Name of seasonality component if previously changed from default 'yearly'.

    Returns:
        a list of matplotlib artists
    """
    artists = []
    if not ax:
        fig = plt.figure(facecolor='w', figsize=figsize)
        ax = fig.add_subplot(111)
    # Compute yearly seasonality for a Jan 1 - Dec 31 sequence of dates.
    days = (pd.date_range(start='2017-01-01', periods=365) +
            pd.Timedelta(days=yearly_start))
    df_y = pd.DataFrame({'ds': days})
    seas = m.predict_seasonal_components(df_y)
    artists += ax.plot(
        df_y['ds'].dt.to_pydatetime(), seas[comp_name], ls='-', c='#0072B2')
    ax.grid(True, which='major', c='gray', ls='-', lw=1, alpha=0.2)
    months = MonthLocator(range(1, 13), bymonthday=1, interval=2)
    ax.xaxis.set_major_formatter(FuncFormatter(
        lambda x, pos=None: '{dt:%B} {dt.day}'.format(dt=num2date(x))))
    ax.xaxis.set_major_locator(months)
    ax.set_xlabel('Day of year')
    ax.set_ylabel('Seasonality: {}'.format(comp_name))
    if m.season_config.mode == 'multiplicative':
        ax = set_y_as_percent(ax)
    return artists


def plot_weekly(m, ax=None, weekly_start=0, figsize=(10, 6), comp_name='weekly'):
    """Plot the yearly component of the forecast.

    Args:
        m (NeuralProphet): fitted model.
        ax (matplotlib axis): matplotlib Axes to plot on.
            One will be created if this is not provided.
        weekly_start (int): specifying the start day of the weekly seasonality plot.
            0 (default) starts the week on Sunday.
            1 shifts by 1 day to Monday, and so on.
        figsize (tuple): width, height in inches.
        comp_name (str): Name of seasonality component if previously changed from default 'weekly'.

    Returns:
        a list of matplotlib artists
    """
    artists = []
    if not ax:
        fig = plt.figure(facecolor='w', figsize=figsize)
        ax = fig.add_subplot(111)
    # Compute weekly seasonality for a Sun-Sat sequence of dates.
    days = (pd.date_range(start='2017-01-01', periods=7) +
            pd.Timedelta(days=weekly_start))
    df_w = pd.DataFrame({'ds': days})
    seas = m.predict_seasonal_components(df_w)
    days = days.day_name()
    artists += ax.plot(range(len(days)), seas[comp_name], ls='-',
                       c='#0072B2')
    ax.grid(True, which='major', c='gray', ls='-', lw=1, alpha=0.2)
    ax.set_xticks(range(len(days)))
    ax.set_xticklabels(days)
    ax.set_xlabel('Day of week')
    ax.set_ylabel('Seasonality: {}'.format(comp_name))
    if m.season_config.mode == 'multiplicative':
        ax = set_y_as_percent(ax)
    return artists
