

def model_run_func(model_cls, run, max_steps, data_collection_period):
    """Run a single model run and collect model and agent data.

    Parameters
    ----------
    model_cls : Type[Model]
        The model class to batch-run
    run: Tuple[int, int, Dict[str, Any]]
        The run id, iteration number, and kwargs for this run
    max_steps : int
        Maximum number of model steps after which the model halts, by default 1000
    data_collection_period : int
        Number of steps after which data gets collected

    Returns
    -------
    List[Dict[str, Any]]
        Return model_data, agent_data from the reporters
    """
    run_id, iteration, kwargs = run
    model = model_cls(**kwargs)
    while model.running and model.schedule.steps <= max_steps:
        model.step()

    data = []

    steps = list(range(0, model.schedule.steps, data_collection_period))
    if not steps or steps[-1] != model.schedule.steps - 1:
        steps.append(model.schedule.steps - 1)

    for step in steps:
        model_data = _collect_data(model, step)
        stepdata = [
            {
                "RunId": run_id,
                "iteration": iteration,
                "Step": step,
                **kwargs,
                **model_data,
            }
        ]
        data.extend(stepdata)

    return data


def _collect_data(model, step):
    """Collect model and agent data from a model using mesas datacollector."""
    dc = model.datacollector
    model_data = {param: values[step] for param, values in dc.model_vars.items()}
    return model_data