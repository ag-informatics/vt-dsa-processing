#!/usr/bin/env python

import pandas as pd
import numpy as np

def load_df (model, subset):

    # Subset can be 'raw_data', 'raw_trials', or ''
    if subset == 'raw_data':
        file_name = 'raw_data_'
    elif subset == 'raw_trials':
        file_name = 'raw_trials_'
    elif subset == 'raw_data_only':
        file_name = 'raw_data_only_'
    elif subset == 'composite':
        file_name = ''
    elif subset == '':
        file_name = ''
    else:
        print('Invalid subset')
        return
    
    # Load data
    model_df = pd.read_csv('model_parameters/{}_parameters.csv'.format(model), 
                           usecols=['Parameter', 'Temporality', 'Importance'])
    attri_df = pd.read_csv('model_parameters/attributes_parameters.csv', 
                           usecols=['Attribute', 'Temporality'])
    codes_df = pd.read_csv('variety_trial_codes/{}codes_summary_processed.csv'.format(file_name),
                            usecols=['code', 'All_Trials'])
    ttool_df = pd.read_csv('model_parameters/translator_tool.csv', 
                           usecols=['Universal Term', 'Domain', 'Situational', 
                                    'Sample Set', 'attributes', 'additionalrdattributes', 'Parent Parameter', model])
    
    # Set index
    model_df.set_index('Parameter', inplace=True)
    attri_df.set_index('Attribute', inplace=True)
    codes_df.set_index('code', inplace=True)
    ttool_df.set_index('Universal Term', inplace=True)

    if subset == 'raw_data' or subset == 'composite':
        addat_df = pd.read_csv('model_parameters/additional_rd_attributes_parameters.csv',
                               usecols=['Attribute', 'Temporality'])
        addat_df.set_index('Attribute', inplace=True)
        # Merge additional attributes dataframe with attributes dataframe, overriding any duplicate rows with the additional attributes dataframe
        attri_df = attri_df.merge(addat_df, how='outer', left_index=True, right_index=True)
        # Merge temporality columns from additional attributes dataframe with attributes dataframe, overriding any duplicate rows with the additional attributes dataframe
        attri_df['Temporality'] = attri_df['Temporality_y'].combine_first(attri_df['Temporality_x'])
        # Drop the additional temporality column
        attri_df.drop(columns=['Temporality_x', 'Temporality_y'], inplace=True)

        # Combine the additional attributes column with the attributes column in the ttool dataframe
        ttool_df['attributes'] = ttool_df['attributes'].combine_first(ttool_df['additionalrdattributes'])
        # Drop the additional attributes column
        ttool_df.drop(columns='additionalrdattributes', inplace=True)
    else:
        # Drop the additional attributes column
        ttool_df.drop(columns='additionalrdattributes', inplace=True)
    
    # Pare down dataframes to only include rows in the sample set
    ttool_df = ttool_df.loc[(ttool_df['Sample Set'] == 'yes')]

    # Combine specific columns from the dataframes to create a new dataframe
    comp_df = ttool_df[['Domain', 'Situational', 'attributes', model, 'Parent Parameter']].copy()

    # if the subset is composite, merge the second codes_df
    if subset == 'composite':
        # load the second codes_df
        codes_df2 = pd.read_csv('variety_trial_codes/{}codes_summary_processed.csv'.format('raw_data_only_'),
                                usecols=['code', 'All_Trials'])
        codes_df2.set_index('code', inplace=True)
        # rename the All_Trials column to All_Trials2
        codes_df2.rename(columns={'All_Trials': 'All_Trials2'}, inplace=True)
        # Merge the second codes_df with the first codes_df
        combined = pd.merge(codes_df, codes_df2, left_index=True, right_index=True, how='outer')
        # Create a new column with the higher of the two All_Trials columns
        combined['All_Trials3'] = combined[['All_Trials', 'All_Trials2']].max(axis=1)
        # Create a new codes_df with the all_trials3 column
        codes_df = combined[['All_Trials3']].copy()
        # Rename the All_Trials3 column to All_Trials
        codes_df.rename(columns={'All_Trials3': 'All_Trials'}, inplace=True)


    # Add map columns from other dataframes to the new dataframe
    comp_df = comp_df.merge(model_df, left_on=model, right_index=True, how='left')
    comp_df = comp_df.merge(attri_df, left_on='attributes', right_index=True, how='left')
    comp_df = comp_df.merge(codes_df, left_on='attributes', right_index=True, how='left')

    # Rename columns
    comp_df.rename(columns={'attributes': 't_param', model: 'm_param', 'Temporality_x': 'm_temp', 'Temporality_y': 't_temp', 'All_Trials':'fraction', 'Parent Parameter': 'parent_parameter'}, inplace=True)

    # lower case column names
    comp_df.columns = comp_df.columns.str.lower()

    # rename index
    comp_df.index.name = 'universal_term'

    return comp_df

def inclusion(comp_df, model, subset):
    # Subset can be 'raw_data', 'raw_trials', or ''
    if subset == 'raw_data':
        file_name = 'raw_data_'
    elif subset == 'raw_trials':
        file_name = 'raw_trials_'
    elif subset == 'raw_data_only':
        file_name = 'raw_data_only_'
    elif subset == 'composite':
        file_name = 'composite_'
    elif subset == '':
        file_name = ''
    else:
        print('Invalid subset')
        return
    # Define a function to sort the inclusion criteria
    comp_df['include'] = np.nan
    # If m_param is null, include is no
    comp_df.loc[comp_df['m_param'].isnull(), 'include'] = 'no'
    # If m_param is not null, include is yes
    comp_df.loc[comp_df['m_param'].notnull(), 'include'] = 'yes'
    # For each parent parameter, if any of the children are included, include the all the children of that parameter
    for parent in comp_df['parent_parameter'].unique():
        if comp_df.loc[comp_df['parent_parameter'] == parent, 'include'].str.contains('yes').any():
            comp_df.loc[comp_df['parent_parameter'] == parent, 'include'] = 'yes'
    # If both t_param and m_param are null, include is no
    comp_df.loc[(comp_df['t_param'].isnull()) & (comp_df['m_param'].isnull()), 'include'] = 'no'
    # Remove rows where include is no
    comp_df = comp_df.loc[comp_df['include'] == 'yes']
    # Drop include column
    comp_df.drop(columns='include', inplace=True)
    # If fraction is null, set to 0
    comp_df.loc[comp_df['fraction'].isnull(), 'fraction'] = 0
    # Add column for score
    comp_df['score'] = np.nan
    # If m_param is not null and t_param is null, score is 2
    comp_df.loc[(comp_df['m_param'].notnull()) & (comp_df['t_param'].isnull()), 'score'] = 2
    # If m_temp and t_temp are not null and the same, score is 2
    comp_df.loc[(comp_df['m_temp'].notnull()) & (comp_df['t_temp'].notnull()) & (comp_df['m_temp'] == comp_df['t_temp']), 'score'] = 2
    # If score is null, score is 0
    comp_df.loc[comp_df['score'].isnull(), 'score'] = 0
    # Reorder columns
    comp_df = comp_df[['domain', 'situational', 'parent_parameter', 
                       'importance', 'fraction', 
                        'm_param', 'm_temp', 
                        't_param', 't_temp', 
                        'score']]
    # sort by universal term
    comp_df.sort_index(inplace=True)
    comp_df.to_csv('scoring_sheets/{a}{b}_comparison_preliminary.csv'.format(a=file_name, b=model))
    return

def add_child_parameters(scores_df, param_df):
    # Create a list of parent parameters with mutually exclusive child parameters
    mut_ex = ['fertilizer application temporality', 'harvest temporality', 'fungicide application temporality',
            'total biomass', 'harvested fruit number', 'harvested yield']

    # Create a list of unique parent parameters, not including nan
    parent_params = param_df['parent_parameter'].dropna().unique()
    for parent in parent_params:
        # Create a df of child scores and fractions for the parent parameter
        child_df = param_df.loc[param_df['parent_parameter'] == parent].copy()
        # Index of the child parameter is the parent parameter
        child_index = parent
        # Child situationality is 'no' if any of the child parameters have a situationality of 'no', otherwise 'yes'
        child_situational = 'no' if 'no' in child_df['situational'].values else 'yes'
        # Child parameters is a list of the child parameters' universal terms
        child_parameters = child_df.index.tolist()

        if child_situational == 'yes':
            # Identify the df row with the highest importance. 
            # If a tie occurs, break the tie by selecting the row with the largest fraction. 
            # If another tie occurs, break the tie by selecting the maximum value of the temporalities in the temp_order list. 
            # If another tie occurs, all but the first term.
            child_df = child_df.sort_values(by=['importance', 'fraction', 't_temp'], ascending=[False, False, False])
            imp_row = child_df.iloc[0].copy()
            # Child domain is the domain of the child parameter with the highest importance
            child_domain = imp_row['domain']
            # Child m_param is the highest importance child parameter
            child_m_param = imp_row['m_param']
            # Child m_temp is the highest importance child parameter value
            child_m_temp = imp_row['m_temp']
            # Child t_param is the highest importance child parameter
            child_t_param = imp_row['t_param']
            # Child t_temp is the highest importance child parameter value
            child_t_temp = imp_row['t_temp']

        else:
            # Identify the df row with 'no' situational with the highest importance. 
            # If a tie occurs, break the tie by selecting the row with the largest fraction. 
            # If another tie occurs, break the tie by selecting the maximum value of the temporalities in the temp_order list. 
            # If another tie occurs, all but the first term.
            child_df = child_df.sort_values(by=['situational', 'importance', 'fraction', 't_temp'], ascending=[False, False, False, False])
            imp_row = child_df.iloc[0].copy()
            # Child domain is the domain of the non-situational child parameter with the highest importance
            child_domain = imp_row['domain']
            # Child m_param is the non-situational child parameter with the highest importance
            child_m_param = imp_row['m_param']
            # Child m_temp is the non-situational child parameter value with the highest importance
            child_m_temp = imp_row['m_temp']
            # Child t_param is the non-situational child parameter with the highest importance
            child_t_param = imp_row['t_param']
            # Child t_temp is the non-situational child parameter value with the highest importance
            child_t_temp = imp_row['t_temp']
        
        if parent in mut_ex:
            # Child importance is the importance of the highest importance child parameter
            child_importance = imp_row['importance']
            # Child value is the sum of the child scores multiplied by the child fractions
            child_value = child_df['score'].mul(child_df['fraction']).sum()
            # Child score is highest child score
            child_score = child_df['score'].max()
            # Child fraction is the sum of the child fractions
            child_fraction = child_df['fraction'].sum()

        else:
            # Child importance is the importance of the highest importance child parameter
            child_importance = imp_row['importance']
            # Calculate child values for each child parameter
            child_values = child_df['score'].mul(child_df['fraction'])
            # Child value is the highest child value
            child_value = child_values.max()
            # Child score is the score of the child parameter with the highest value
            child_score = child_df.loc[child_values.idxmax(), 'score']
            # Child fraction is the fraction of the child parameter with the highest value
            child_fraction = child_df.loc[child_values.idxmax(), 'fraction']
            
        # Create a df of the child parameters

        row_df = pd.DataFrame({'m_param': child_m_param,
                                'm_temp': child_m_temp,
                                't_param': child_t_param,
                                't_temp': child_t_temp,
                                'score': child_score,
                                'fraction': child_fraction,
                                'importance': child_importance,
                                'domain': child_domain,
                                'situational': child_situational,
                                'child_parameters': [child_parameters],
                                'value': child_value}, 
                                index=[child_index])

        # Add the row to the scores_df dataframe
        scores_df = pd.concat([scores_df, row_df])



    return scores_df

def load_scored_df (model, subset):
    # Subset can be 'raw_data', 'raw_trials', or ''
    if subset == 'raw_data':
        file_name = 'raw_data_'
    elif subset == 'raw_trials':
        file_name = 'raw_trials_'
    elif subset == 'raw_data_only':
        file_name = 'raw_data_only_'
    elif subset == 'composite':
        file_name = 'composite_'
    elif subset == '':
        file_name = ''
    else:
        print('Invalid subset')
        return
    # Load data
    param_df = pd.read_csv('scoring_sheets/reviewed/{a}{b}_comparison_reviewed.csv'.format(a=file_name, b=model), index_col='universal_term')
    
    # Drop rows with a score value of 0
    param_df = param_df.loc[param_df['score'] != 0].copy()

    # Convert the importance column to numeric on a scale of 1-4
    param_df['importance'] = param_df['importance'].map({np.nan: 0, 'low': 1, 'medium': 2, 'high': 3, 'critical': 4})

    # If m_param is empty, set it to t_param and vice versa
    param_df['m_param'] = param_df['m_param'].fillna(param_df['t_param'])
    param_df['t_param'] = param_df['t_param'].fillna(param_df['m_param'])

    # if m_temp is empty, set it to t_temp and vice versa
    param_df['m_temp'] = param_df['m_temp'].fillna(param_df['t_temp'])
    param_df['t_temp'] = param_df['t_temp'].fillna(param_df['m_temp'])
    
    # Create a dataframe that includes only the parameters with a null value for the parent_parameter column
    scores_df = param_df.loc[param_df['parent_parameter'].isnull()].copy()

    # change the name of the parent_parameter column to child_parameters
    scores_df.rename(columns={'parent_parameter': 'child_parameters'}, inplace=True)

    # Add a column that is equal to the fraction column multiplied by the score column
    scores_df['value'] = scores_df['fraction'] * scores_df['score']

    # Add child parameters to the scores_df dataframe
    scores_df = add_child_parameters(scores_df, param_df)
    
    # Create a param score column equal to the value column multiplied by the importance column
    scores_df['param_score'] = scores_df['value'] * scores_df['importance']
    # Create a potential score column equal to the importance column multiplied by two
    scores_df['potential_score'] = scores_df['importance'] * 2
    # Add a column marking failure for any parameter with a value of 0
    scores_df['failure'] = scores_df['value'] == 0
    
    # save to csv
    scores_df.to_csv('scoring_sheets/final_parameters/{a}{b}_parameter_scores.csv'.format(a=file_name, b=model), index=True)

    return scores_df

def summarize_scores (scores_df, model, subset):
    # Subset can be 'raw_data', 'raw_trials', or ''
    if subset == 'raw_data':
        file_name = 'raw_data_'
    elif subset == 'raw_trials':
        file_name = 'raw_trials_'
    elif subset == 'raw_data_only':
        file_name = 'raw_data_only_'
    elif subset == 'composite':
        file_name = 'composite_'
    elif subset == '':
        file_name = ''
    else:
        print('Invalid subset')
        return

    # Create a dataframe with only parameters with a situationality of 'no'
    generic_df = scores_df.loc[scores_df['situational'] == 'no'].copy()
    # Create a dataframe with only parameters with a situationality of 'no' and importance of 4
    core_df = scores_df.loc[(scores_df['situational'] == 'no') & (scores_df['importance'] == 4)].copy()
    # Create a dataframe with only parameters with a situationality of 'yes'
    situational_df = scores_df.loc[scores_df['situational'] == 'yes'].copy()

    # Create a dataframe to summarize the scoring
    attained_score = scores_df['param_score'].sum()
    possible_score = scores_df['potential_score'].sum()
    score_fraction = attained_score / possible_score
    total_variables = scores_df.shape[0]
    total_failures = scores_df.loc[scores_df['failure'] == True].shape[0]
    total_failure_rate = total_failures / total_variables

    # Get the total number of core failures
    core_failure = core_df.loc[core_df['failure'] == True].shape[0]
    # Get the total number of core parameters
    core_num = core_df.shape[0]
    core_failure_rate = core_failure / core_num
    total_situational = situational_df.shape[0]
    situational_critical = situational_df.loc[situational_df['importance'] == 4].shape[0]
    situational_critical_failure = situational_df.loc[situational_df['importance'] == 4, 'failure'].shape[0]
    if situational_critical == 0:
        situational_critical_failure_rate = 0
    else:
        situational_critical_failure_rate = situational_critical_failure / situational_critical



    summary_df = pd.DataFrame({'model': model,
                            'subset': subset,
                            'total_variables': total_variables,
                            'total_failures': total_failures,
                            'total_failure_rate': total_failure_rate,
                            'core_failure': core_failure,
                            'core_num': core_num,
                            'core_failure_rate': core_failure_rate,
                            'total_situational': total_situational,
                            'situational_critical': situational_critical,
                            'situational_critical_failure': situational_critical_failure,
                            'situational_critical_failure_rate': situational_critical_failure_rate,
                            'attained_score': attained_score,
                            'possible_score': possible_score,
                            'suitability_score': score_fraction
                            }, index=[0])

    # save to csv
    summary_df.to_csv('scoring_sheets/final_datasets/{a}{b}_summary.csv'.format(a=file_name, b=model), index=False)