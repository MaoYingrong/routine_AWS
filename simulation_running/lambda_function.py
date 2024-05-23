from functools import partial
from helper import model_run_func
from model import OrgNetwork
import boto3
import mysql.connector
from collections.abc import Iterable, Mapping
from typing import Any, Union
import itertools


rds = boto3.client('rds')
rds.get_waiter('db_instance_available') \
   .wait(DBInstanceIdentifier='final-instance')
ddb = rds.describe_db_instances()['DBInstances'][0]
ENDPOINT = ddb['Endpoint']['Address']
PORT = ddb['Endpoint']['Port']
DB_NAME = ddb['DBName']

conn =  mysql.connector.connect(host=ENDPOINT, 
                                user="username", 
                                passwd="password", 
                                port=PORT, 
                                database=DB_NAME)

cur = conn.cursor()


sql_insert_query = """
INSERT INTO simulation_data 
    (RunId, iteration, Step, num_tasks, num_nodes, num_new_edges, 
    skills_proportion, prob_memory, availability, combination_id, 
    actor_sequence_lst, time_lst) 
VALUES 
    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
    RunId = %s,
    iteration = %s, 
    Step = %s, 
    num_tasks = %s, 
    num_nodes = %s, 
    num_new_edges = %s, 
    skills_proportion = %s, 
    prob_memory = %s, 
    availability = %s, 
    combination_id = %s,
    actor_sequence_lst = %s, 
    time_lst = %s;
"""


# Create a unique ID for each combination
def make_combination_list(parameters: Mapping[str, Union[Any, Iterable[Any]]],
) -> list[dict[str, Any]]:
    """Create model kwargs from parameters dictionary.

    Parameters
    ----------
    parameters : Mapping[str, Union[Any, Iterable[Any]]]
        Single or multiple values for each model parameter name

    Returns
    -------
    List[Dict[str, Any]]
        A list of all kwargs combinations.
    """
    parameter_list = []
    for param, values in parameters.items():
        if isinstance(values, str):
            # The values is a single string, so we shouldn't iterate over it.
            all_values = [(param, values)]
        else:
            try:
                all_values = [(param, value) for value in values]
            except TypeError:
                all_values = [(param, values)]
        parameter_list.append(all_values)

    all_kwargs = itertools.product(*parameter_list)

    kwargs_list = []
    for kwargs in all_kwargs:
        kwargs_dict = dict(kwargs)
        # Create a unique identifier for each combination
        combination_value = ""
        for key, value in kwargs_dict.items():
            combination_value += f"{key}{value}"
        kwargs_dict['combination_id'] = combination_value
        kwargs_list.append(kwargs_dict)

    return kwargs_list



def lambda_handler(event, context):
    """
    Lambda handler for the model
    event:{"key": 10} 10/20/30/40/50/60/70/80/90/100
    Store the results in the RDS database
    """
    runs_list = []
    run_id = 0

    iteration = event.pop("iterations")
    combination_list = make_combination_list(event)
    
    for iteration in range(iteration):
        for kwargs in combination_list:
            runs_list.append((run_id, iteration, kwargs))
            run_id += 1

    process_func = partial(
        model_run_func,
        OrgNetwork,
        max_steps=100,
        data_collection_period=-1,
    )

    for run in runs_list:
        reusults_lst = process_func(run)
        for data in reusults_lst:
            del data["Time"]
            data["time_lst"] = str(data["time_lst"])
            data["actor_sequence_lst"] = str(data["actor_sequence_lst"])
            cur.execute(sql_insert_query, (tuple(data.values())*2))
            
    conn.commit()
    conn.close()
    print("Data inserted successfully for ", event["num_nodes"])
    
# if __name__ == "__main__":

#     event = {"iterations": 50,
#              "num_tasks": 8,
#              "num_nodes": 20,
#              "num_new_edges": 2,
#              "skills_proportion": np.linspace(0.1, 0.2, 2),
#              "prob_memory": 0.5,
#              "availablity": 0.5}

#     lambda_handler(event, None)
#     cur.execute("SELECT COUNT(*) FROM simulation_data;")
#     print(cur.fetchall())
#     conn.close()




