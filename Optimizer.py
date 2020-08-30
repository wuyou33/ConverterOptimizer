from Converter.BoostHalfBridge import BoostHalfBridgeInverter
from Converter.Components import *
from scipy.optimize import minimize


class GeneticOptimizer:

    def __init__(self, selected_components, circuit_features, safety_params):
        self.Switches = []
        self.Diodes = []
        self.Cores = selected_components['Cores']
        self.Cables = selected_components['Cables']
        self.Dissipators = None
        self.Capacitors = []
        self.CircuitFeatures = circuit_features
        self.SafetyParams = safety_params
        self.population = []
        self.population_size = None

        self.preselection(selected_components['Switches'], selected_components['Diodes'], selected_components['Capacitors'])

    # Removes elements from the list that will not under any circuntances, be feasible in the given circuit.
    def preselection(self, switches, diodes, capacitors):

        # Preselection of capacitors.
        c = []
        for n in range(0, 4):
            c.append([])

        for capacitor in capacitors:
            if capacitor.Vmax > self.SafetyParams['Vc']*max(self.CircuitFeatures['Vi']['Min']*self.CircuitFeatures['D']['Max']/(1-self.CircuitFeatures['D']['Max']), self.CircuitFeatures['Vi']['Max']*self.CircuitFeatures['D']['Min']/(1-self.CircuitFeatures['D']['Min'])):
                c[0].append(capacitor)
            if capacitor.Vmax > self.SafetyParams['Vc']*self.CircuitFeatures['Vi']['Max']:
                c[1].append(capacitor)
            if capacitor.Vmax > self.SafetyParams['Vc']*self.CircuitFeatures['Vo']/4:
                c[2].append(capacitor)
                c[3].append(capacitor)
        self.Capacitors = c

        # Preselection of diodes.
        d = []
        for n in range(0, 2):
            d.append([])
        for diode in diodes:
            if diode.Vmax > self.SafetyParams['Vd']*self.CircuitFeatures['Vo']:
                d[0].append(diode)
                d[1].append(diode)
        self.Diodes = d
        #
        # # Preselection of switches.
        # s = []
        # for n in range(0, 2):
        #     s.append([])
        # for switch in switches:
        #     if switch.Vmax > self.SafetyParams['Vs'] * self.CircuitFeatures['Vi']['Max']/(1-self.CircuitFeatures['D']['Min']):
        #         s[0].append(capacitor)
        #         s[1].append(capacitor)
        # for n in range(0, 2):
        #     self.Switches.append(s[n])

    def generate_circuit(self):
        # Chooses the switches, capacitors and diodes for the circuit.
        switches = []
        for n in range(0, 2):
            switches.append(np.random.choice(self.Switches[n]))
        capacitors = []
        for n in range(0, 4):
            capacitors.append(np.random.choice(self.Capacitors[n]))
        diodes = []
        for n in range(0, 2):
            diodes.append(np.random.choice(self.Diodes[n]))

        # Builds a feasible transformer.
        feasible = False
        transformer = None
        while not feasible:
            core = np.random.choice(self.Cores)
            cables = [np.random.choice(self.Cables), np.random.choice(self.Cables)]
            found = False
            n = [0, 0]
            while not found:
                n = [np.random.randint(1, 200), np.random.randint(1, 200)]
                a = self.CircuitFeatures['Vi']['Nominal'] >= self.CircuitFeatures['Vo']
                b = n[0] >= n[1]
                found = (a and b) or (not a and not b)
            ncond = [np.random.randint(1, 50), np.random.randint(1, 50)]
            transformer = Transformer(core, cables, n, ncond)
            feasible = transformer.is_feasible(self.SafetyParams['ku']['Transformer'])

        # Builds a feasible entrance inductor.
        feasible = False
        entrance_inductor = None
        while not feasible:
            core = np.random.choice(self.Cores)
            cable = np.random.choice(self.Cables)
            n = np.random.randint(1, 200)
            ncond = np.random.randint(1, 50)
            entrance_inductor = Inductor(core, cable, n, ncond)
            feasible = entrance_inductor.is_feasible(self.SafetyParams['ku']['EntranceInductor'])

        # Builds a feasible auxiliary inductor.
        feasible = False
        auxiliary_inductor = None
        while not feasible:
            core = np.random.choice(self.Cores)
            cable = np.random.choice(self.Cables)
            n = np.random.randint(1, 200)
            ncond = np.random.randint(1, 50)
            auxiliary_inductor = Inductor(core, cable, n, ncond)
            feasible = auxiliary_inductor.is_feasible(self.SafetyParams['ku']['AuxiliaryInductor'])


        # dissipators = [np.random.choice(self.Dissipators), np.random.choice(self.Dissipators)]
        new_circuit = BoostHalfBridgeInverter(transformer, entrance_inductor, auxiliary_inductor, self.CircuitFeatures, switches, diodes, capacitors)
        return new_circuit

    # Ok
    def optimize(self, population_size=50, epochs=50, starting_mutation_rate=0.5, mutation_decay_rate = 0.01, minimal_mutation_rate=0.1, crossover_rate=0.5, elitist_rate=0.1, kill_rate=0.1, solution_size=2):
        self.population = []
        self.population = self.create_population(population_size)
        best_loss = self.CircuitFeatures['Po']*np.zeros(solution_size)
        solution = np.random.choice[self.population, solution_size]

        mutation_rate = starting_mutation_rate

        for epoch in range(0, epochs):
            [losses, feasible] = self.test_population(population_size)                      # Ok
            [sorted_indexes, best_loss, solution] = self.sort_population_idexes(
                population_size, solution_size, losses, feasible, best_loss, solution)      # Ok
            elite_indexes = sorted_indexes[0:round(self.population_size * elitist_rate)]
            self.kill_population(elite_indexes, kill_rate, feasible)                        # Ok
            self.cross_population(losses, crossover_rate, elite_indexes)                    # Ok
            self.mutate_population(mutation_rate)
            mutation_rate = mutation_rate - mutation_decay_rate
            if mutation_rate <= minimal_mutation_rate:
                mutation_rate = minimal_mutation_rate
        return solution

    # Ok
    def create_population(self, population_size):
        self.population_size = population_size
        population = []
        for index in range(0, self.population_size):
            population.append(self.generate_circuit())
        return population

    # Tests the population and return two arrays, one with the losses and the other with the feasibility.
    # Ok
    def test_population(self):
        feasible = np.zeros(self.population_size, dtype=np.bool)
        losses = np.zeros(self.population_size)
        for index in range(0, self.population_size):
            circuit = self.population[index]
            loss = circuit.optimize()
            if circuit.solution_is_feasible():
                feasible[index] = True
            losses[index] = loss
        return [losses, feasible]

    # Sorts the population indexes from best to worst. So population[indexes[0]] is the best circuit. It also finds if
    # there is a solution better than the best found so far, and if so, saves this solution
    # Ok
    def sort_population_indexes(self, solution_size, losses, feasible, best_loss, solution):
        # Sorts the losses
        sorted_indexes = np.zeros(self.population_size, dtype=np.int)
        for index in range(0, self.population_size):
            best = np.Infinity
            for sorting_index in range(index, self.population_size):
                if losses[sorting_index] < best:
                    best = losses[sorting_index]
                    aux = losses[index]
                    losses[index] = losses[sorting_index]
                    losses[sorting_index] = aux
                    sorted_indexes[index] = sorting_index

        # Verifies if a member of the current population is better then one in the Solution vector.
        arr = best_loss
        pop_arr = solution
        size = solution_size
        for index in range(0, solution_size):
            arr.append(losses[sorted_indexes[index]])
            if feasible[sorted_indexes[index]]:
                pop_arr.append(self.population[sorted_indexes[index]])
                size += 1

        for index in range(0, solution_size):
            lowest = arr[-1]
            for j in range(index, size):
                if arr[j] <= lowest:
                    lowest = arr[j]
                    swap = j
            temp1 = arr[swap]
            temp2 = pop_arr[swap]
            arr[swap] = arr[index]
            pop_arr[swap] = pop_arr[index]
            arr[index] = temp1
            pop_arr[index] = temp2

        best_loss = arr[0:solution_size]
        solution = pop_arr[0:solution_size]

        return [sorted_indexes, best_loss, solution]

    def kill_population(self, elite_indexes, kill_rate, feasible):
        for index in range(0, self.population_size):
            if not feasible[index]:
                self.population[index] = self.generate_circuit()

        for index in range(0, round(self.population_size*kill_rate)):
            found = False
            kill_index = 0
            while not found:
                kill_index = np.random(0, self.population_size)
                if kill_index not in elite_indexes:
                    found = True
            self.population[kill_index] = self.generate_circuit()

    def cross_population(self, losses, crossover_rate, elite_indexes):
        rescaled_losses = rescale(losses, [0.01, 0.1], lambda x: 1/x)
        rescaled_losses = rescaled_losses/sum(rescaled_losses)
        for crossing in range(0, round(self.population_size*crossover_rate)):
            parent_index1 = np.random.choice(self.population_size, rescaled_losses)
            parent_index2 = np.random.choice(self.population_size, rescaled_losses)

            found = False
            child_index = 0
            while not found:
                child_index = np.random.choice(self.population_size)
                found = not (child_index in elite_indexes)
            self.population[child_index] = self.cross_over(parent_index1, parent_index2)

    def cross_over(self, parent1, parent2):
        gene_types = ['primary_cable', 'secondary_cable', 'transformer_core', 'primary_winding', 'secondary_winding',
                      'primary_parallel_wires', 'secondary_parallel_wires',
                      'entrance_inductor_cable', 'entrance_inductor_winding',
                      'entrance_inductor_parallel_wires', 'entrance_inductor_inductor_core',
                      'auxiliary_inductor_cable', 'auxiliary_inductor_winding',
                      'auxiliary_inductor_parallel_wires', 'auxiliary_inductor_core'
                      'c1', 'c2', 'c3', 'c4', 'd3', 'd4', 's1', 's2'
                     ]
        gene_types = np.shuffle(gene_types)
        parent2_gene_types = gene_types[0:11]

        offspring = self.population[parent1]

        for gene_type in parent2_gene_types:
            parent2_gene = self.population[parent2].get_parameter(gene_type)
            offspring.set_parameter(gene_type, parent2_gene)

        if not offspring.Transformer.is_feasible(self.SafetyParams['ku']['Transformer']):
            offspring.Transformer.recalculate_winding(self.SafetyParams['ku']['Transformer'], self.CircuitFeatures)
        if not offspring.EntranceInductor.is_feasible(self.SafetyParams['ku']['EntranceInductor']):
            offspring.EntranceInductor.recalculate_winding(self.SafetyParams['ku']['EntranceInductor'])
        if not offspring.AuxiliaryInductor.is_feasible(self.SafetyParams['ku']['AuxiliaryInductor']):
            offspring.AuxiliaryInductor.recalculate_winding(self.SafetyParams['ku']['AuxiliaryInductor'])

        return offspring

    def mutate_population(self, mutation_rate):
        x = 2
        # Nada


def OptimizeConverter(converter, epochs=100, algorithm='SLSQP', input_scale=None):
    if input_scale is None:
        input_scale = [1, 1e8, 1e11]
    converter.first_run = True

    Dmin = converter.Features['D']['Min']
    Dmax = converter.Features['D']['Max']
    Vmin = converter.Features['Vi']['Min']
    Vmax = converter.Features['Vi']['Max']
    Po = converter.Features['Po']
    Vo = converter.Features['Vo']

    # Verifies the upper bound for the frequency.
    f_upper = [(2*converter.EntranceInductor.Penetration_base/converter.EntranceInductor.Cable.Dcu)**2]
    f_lower = [
        max(((1-Dmin)**2)/(Vmax*Dmin), ((1-Dmax)**2)/(Vmin*Dmax))*Po/(4*converter.Capacitors[0].C*converter.Features['dVc1']),
        max((1-Dmax)/Vmin**2, (1-Dmin)/Vmax**2)*Po/(converter.Capacitors[1].C*converter.Features['dVc2']),
        Dmax*Po/(converter.Capacitors[2].C*converter.Features['dVo_max']*Vo**2),
        (1-Dmin)*Po/(converter.Capacitors[3].C*converter.Features['dVo_max']*Vo**2)
    ]

    print(max(f_lower))

    bounds = ((max(f_lower), min(f_upper)), (1e7*0.0002562, 1e9*0.0002562), (1e10*0.5e-6, 1e12*0.5e-6))

    print(bounds)

    x0 = np.array([40e3, 1e8*0.0002562, 1e11*0.5e-6])
    sol = minimize(
        lambda x: converter.compensated_total_loss([a/b for a, b in zip(x, input_scale)]),
        x0,
        method=algorithm,
        tol = 1e-10,
        options={'maxiter': epochs, 'disp': True},
        bounds=bounds,
        constraints={'fun': lambda x: converter.total_constraint([a/b for a, b in zip(x, input_scale)]), 'type': 'ineq'}
    )
    print(sol)
    return sol


def rescale(vector, bounds, function=None):
    xmax = max(vector)
    xmin = min(vector)
    a = (bounds[1] - bounds[0]) / (xmax - xmin)
    b = (xmax * bounds[0] - xmin * bounds[1]) / (xmax - xmin)
    rescaled = np.zeros(np.size(vector))
    for index in range(0, np.size(vector)):
        rescaled[index] = a * vector[index] + b
        if function:
            rescaled[index] = function(rescaled[index])
    return rescaled


def clamp(number, lower_bound, upper_bound=None):
    if number < lower_bound:
        return lower_bound
    if number > upper_bound:
        return upper_bound
    return number
