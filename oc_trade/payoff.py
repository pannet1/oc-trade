import opstrat as op

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
op.multi_plotter(spot_range=100, spot=17784,
                 op_list=op_list, save=True, file='fig.png')
SystemExit()
