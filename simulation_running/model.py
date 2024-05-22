import math
from enum import Enum
import mesa
import random
import networkx as nx


class Time(Enum):
    WORKING = 3
    SEARCHING = 1


class ActorAgent(mesa.Agent):
    """
    Individual Agent definition and its properties/interaction methods
    """

    def __init__(
        self,
        unique_id,
        model,
        prob_memory,
        availablity
    ):
        super().__init__(unique_id, model)
        self.memory = {}
        self.skills_set = []
        self.prob_memory = prob_memory
        self.aviablity = availablity
        self.parent = None
        self.explored = False
    

    def have_skill(self, task):
        return task in self.skills_set
    

    def know_others(self, task):
        try:
            actors_lst = self.memory[task]
            return True, random.choice(actors_lst)
        except KeyError:
            return False, None
        

    def update_memory(self, task, agent, prob_memory):
        if self.model.random.random() < prob_memory:
            try:
                self.memory[task].append(agent)
            except KeyError:
                self.memory[task] = [agent]


    def update_all_memory(self, task):
        working_agent = self
        agent = self.parent
        while agent:
            agent.update_memory(task, working_agent, self.prob_memory)
            agent = agent.parent


    def available(self):
        return self.model.random.random() < self.aviablity


    def step(self, task):
        """Actors' decision-making process"""
        task = self.model.tasks_lst[0]
        know_others, actor = self.know_others(task)

        if not self.have_skill(task) and not know_others:
            return False, self.model.grid.get_neighbors(
                self.pos, include_center=False
                )
        
        if self.have_skill(task):
            working_agent = self
        elif know_others:
            working_agent = actor

        return True, [working_agent]
    
  

class OrgNetwork(mesa.Model):
    """
    A network model of an organization with agents that can solve problems.
    """

    def __init__(
        self,
        combination_id,
        num_tasks = 8,
        num_nodes=20,
        num_new_edges=3,
        skills_proportion=0.1,  #the proportion of agents with skills
        prob_memory=0.6,
        availablity=0.5
    ):
        super().__init__()
        self.num_tasks = num_tasks
        self.num_nodes = num_nodes
        self.num_new_edges = num_new_edges
        self.skills_proportion = skills_proportion

        self.G = nx.barabasi_albert_graph(n=self.num_nodes, m=self.num_new_edges)
        self.grid = mesa.space.NetworkGrid(self.G)

        self.schedule = mesa.time.BaseScheduler(self)
        self.agent_list = []
        self.routine_lst = [] 
        self.time_lst = []

        self.datacollector = mesa.datacollection.DataCollector(
            model_reporters={"Time": "time",
                             "actor_sequence_lst": "routine_lst",
                             "time_lst": "time_lst"},
        )

        # Create agents
        for i, node in enumerate(self.G.nodes()):
            a = ActorAgent(i, self, prob_memory, availablity)
            # Add the agent to the node
            self.grid.place_agent(a, node)
            self.agent_list.append(a)
        
        num_agents = math.ceil(self.num_nodes * self.skills_proportion) 
        for skill in range(self.num_tasks):
            for agent in self.random.sample(self.agent_list, num_agents):
                agent.skills_set.append(skill)

        self.initialize_problem()
        self.running = True
        self.datacollector.collect(self)

    
    def initialize_problem(self):
        """
        Initialize the problem by randomly selecting an agent to start the search.
        """
        initial_agent = self.random.choice(self.agent_list)
        initial_agent.explored = True
        self.searching_list = [initial_agent]
        self.status = "initial"  # The model has three status: initial, working, searching
        self.routine = {}
        self.tasks_lst = list(range(self.num_tasks))
        self.time = 0


    def step(self):

        if self.status == "working":
            self.time += Time.WORKING.value
            self.routine[self.tasks_lst[0]] = self.searching_list[0].unique_id
            self.searching_list[0].update_all_memory(self.tasks_lst[0])
            self.tasks_lst.pop(0)
            self.status = "searching"
            for agent in self.agent_list:
                agent.parent = None
                agent.explored = False

            if len(self.tasks_lst) == 0:
                self.schedule.steps += 1
                self.routine_lst.append(self.routine)
                self.time_lst.append(self.time)
                self.initialize_problem()
                
        current_actor = self.searching_list[0]
        result, actors = current_actor.step(self.tasks_lst[0])
        self.time += Time.SEARCHING.value

        if result:
            if actors[0].available():
                self.searching_list = [actors[0]]
                self.status = "working"
            else:
                self.searching_list.pop(0)
                self.searching_list.append(actors[0])
                self.status = "searching"
        else:
            self.searching_list.pop(0)
            for actor in actors:
                if actor.explored == False and current_actor.parent != actor:
                    actor.explored = True
                    actor.parent = current_actor
                    self.searching_list.append(actor)
            self.status = "searching"

        self.datacollector.collect(self)


    def run_model(self, n_problems):
        while len(self.routine_lst) < n_problems:
            self.step()
        return self.routine_lst
            

                
    



