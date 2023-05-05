import plotly.graph_objs as go
import uvicorn
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

app = FastAPI()
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


op_1 = {'op_type': 'p', 'strike': 17500,
        'tr_type': 'b', 'op_pr': 30.65, 'contract': 5}
op_2 = {'op_type': 'p', 'strike': 17600,
        'tr_type': 's', 'op_pr': 59.61, 'contract': 10}
op_3 = {'op_type': 'c', 'strike': 17700,
        'tr_type': 'b', 'op_pr': 62.55, 'contract': 5}
op_4 = {'op_type': 'p', 'strike': 17700,
        'tr_type': 'b', 'op_pr': 94.00, 'contract': 5}
op_5 = {'op_type': 'c', 'strike': 17800,
        'tr_type': 's', 'op_pr': 24.45, 'contract': 10}
op_6 = {'op_type': 'c', 'strike': 17900,
        'tr_type': 's', 'op_pr': 7.45, 'contract': 5}
op_list = [op_1, op_2, op_3, op_4, op_5, op_6]
underlying_price = 17650


@app.get("/chart")
async def read_chart(request: Request, underlying_price: float = underlying_price, op_list: list = op_list, multiplier: int = 50):
    # Generate the range of underlying prices
    underlying_range = range(underlying_price-500, underlying_price+500)

# Calculate the combined payoff
    payoffs = []
    for underlying_price in underlying_range:
        payoff = 0
        for op in op_list:
            tr_type = 1 if op['tr_type'] == 'b' else -1
            # calculate the premium paid based on transaction type
            premium_paid = op['op_pr'] * tr_type
            if op['op_type'] == 'c':
                breakeven_price = op['strike'] + premium_paid
                if underlying_price > breakeven_price:
                    payoff += (underlying_price - op['strike']) * \
                        (tr_type * op['contract']) * 50 - \
                        premium_paid  # deduct the premium paid from the payoff
            elif op['op_type'] == 'p':
                breakeven_price = op['strike'] - premium_paid
                if underlying_price < breakeven_price:
                    payoff += (op['strike'] - underlying_price) * \
                        (tr_type * op['contract']) * 50 - \
                        premium_paid  # deduct the premium paid from the payoff
        payoffs.append(payoff)

    traces = []
    for op in op_list:
        tr_type = 1 if op['tr_type'] == 'b' else -1
        payoff = []
        for underlying_price in underlying_range:
            # calculate the premium paid based on transaction type
            premium_paid = op['op_pr'] * tr_type
            if op['op_type'] == 'c':
                payoff.append(
                    max(underlying_price - op['strike'], 0) * (tr_type * op['contract'] * multiplier) - premium_paid)  # deduct the premium paid from the payoff
            elif op['op_type'] == 'p':
                payoff.append(
                    max(op['strike'] - underlying_price, 0) * (tr_type * op['contract'] * multiplier) - premium_paid)  # deduct the premium paid from the payoff
        trace = go.Scatter(x=list(underlying_range), y=payoff,
                           mode='lines', name=f"{op['op_type'].upper()}@{op['strike']}")
        traces.append(trace)

# Calculate the combined payoff
    combined_payoff = [sum(x) for x in zip(*[trace.y for trace in traces])]
    combined_trace = go.Scatter(x=list(underlying_range), y=combined_payoff,
                                mode='lines', name='Combined Payoff', line=dict(color='black', width=2))
    traces.append(combined_trace)

# Create a trace for the underlying price
    underlying_trace = go.Scatter(x=[underlying_price, underlying_price], y=[min(combined_payoff), max(combined_payoff)],
                                  mode='lines', name='Underlying Price', line=dict(dash='dash'))
    traces.append(underlying_trace)

# Create annotations for the underlying price and payoffs
    annotations = [
        dict(xref='paper', yref='paper', x=0.02, y=0.98,
             xanchor='left', yanchor='top', text=f"Underlying Price: {underlying_price}", showarrow=False),
        dict(xref='paper', yref='paper', x=0.98, y=0.02,
             xanchor='right', yanchor='bottom', text="Combined Payoff", showarrow=False),
    ]

    for i, op in enumerate(op_list):
        annotations.append(dict(x=op['strike'], y=0, xref='x', yref='y',
                                text=f"{op['op_type'].upper()}@{op['strike']}", ax=0, ay=-20))

    # Set the layout
    fig = go.Figure(data=traces, layout=go.Layout(
        title='Option Payoff Diagram',
        xaxis_title='Underlying Price',
        yaxis_title='Payoff',
        yaxis=dict(
            range=[min(combined_payoff), max(combined_payoff)]
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=50, r=50, t=80, b=50),
        shapes=[
            dict(type='line', xref='x', yref='y',
                 x0=underlying_price, y0=min(combined_payoff),
                 x1=underlying_price, y1=max(combined_payoff),
                 line=dict(color='black', width=2, dash='dash')),
            dict(type='line', xref='paper', yref='y',
                 x0=0, y0=0, x1=1, y1=0,
                 line=dict(color='gray', dash='dash')),
            dict(type='line', xref='x', yref='paper',
                 x0=min(underlying_range), y0=0, x1=max(underlying_range), y1=1,
                 line=dict(color='black', width=1)),
            dict(type='line', xref='x', yref='paper',
                 x0=underlying_price, y0=0, x1=underlying_price, y1=1,
                 line=dict(color='gray', dash='dash')),
        ],
    ))
    for trace in fig.data:
        if trace.name == 'Combined Payoff':
            trace.line.color = 'black'
            trace.line.width = 4
        else:
            trace.showlegend = True

    return HTMLResponse(content=fig.to_html(include_plotlyjs='cdn'), status_code=200)

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8000)
