import rubi as Rubi

def get_aid_data(rubi, aid, bin_size, start_time=None, end_time=None): 

    # get the gas spend data
    gas = rubi.data.market_aid_optimism.get_aid_gas_spend_binned(aid = aid)

    # get the aid history 
    aid_history = rubi.data.market_aid_optimism_processing.analyze_aid_history(aid = aid, start_time = start_time, end_time = end_time)

    # add the gas spend data to the aid history
    aid_history['data']['gas_spend_usd'] = aid_history['data']['timestamp'].map(gas).fillna(0)
    aid_history['data']['total_gas_spend_usd'] = aid_history['data']['gas_spend_usd'].cumsum()

    # for each asset, calculate a relative balance based upon the asset price and the total balance
    for asset in aid_history['tokens']: 
        aid_history['data'][f'{asset}_relative_balance'] = (aid_history['data'][f'{asset}_balance'] * aid_history['data'][f'{asset}_price']) / aid_history['data']['total_balance_usd']

    # calculate the delta net of gas spend
    aid_history['data']['delta_net_gas_usd'] = aid_history['data']['total_delta_usd'] - aid_history['data']['total_gas_spend_usd']

    return aid_history
