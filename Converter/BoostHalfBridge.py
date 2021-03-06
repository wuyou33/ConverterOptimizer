import Converter.Restrictions as Restrictions
import Converter.Losses as Losses
import Converter.auxiliary_functions as Functions
import numpy as np
import math
from scipy.spatial import distance


class BoostHalfBridgeInverter:

    def __init__(self, transformer, entrance_inductor, auxiliary_inductor, circuit_features, switches, diodes, capacitors, safety_params,dissipators=None):
        self.design_features = circuit_features
        self.design_features['D'] = {
            'Max': 1-(self.design_features['Vi']['Min']*transformer.Ratio/self.design_features['Vo']),
            'Min': 1-(self.design_features['Vi']['Max']*transformer.Ratio/self.design_features['Vo'])
        }
        self.design_features['D']['Expected'] = 1-(self.design_features['Vi']['Nominal']*transformer.Ratio/self.design_features['Vo'])
        self.safety_params = safety_params

        self.loss_functions = Losses.loss_function_map
        self.loss_functions_activation_map = {
            'Transformer': {'Core': True, 'Primary': True, 'Secondary': True},
            'EntranceInductor': {'Core': True, 'Cable': True},
            'AuxiliaryInductor': {'Core': True, 'Cable': True},
            'Capacitors': {'C1': True, 'C2': True, 'C3': True, 'C4': True},
            'Diode': {'D3': True, 'D4': True},
            'Switches': {'S1': True, 'S2': True}
        }

        self.restriction_functions = []
        for restriction in Restrictions.Restrictions:
            self.restriction_functions.append({'active': True, 'function': restriction})
        
        # Componentes
        self.transformer = transformer
        self.entrance_inductor = entrance_inductor
        self.auxiliary_inductor = auxiliary_inductor
        self.capacitors = capacitors
        self.diodes = diodes
        self.switches = switches
        self.dissipators = dissipators

        # Variáveis referentes à simulação.
        self.last_calculated_operating_point = [0,0,0]
        self.last_calculated_loss = None
        self.last_calculated_efficiency = None
        self.calculated_values = {}

        self.unfeasible_operating_points = []
        self.operating_points_scale = []
        self.number_of_unfeasible_points = 0


    def unfeasible_points_barrier(self, X):
        var = 0
        for point in self.unfeasible_operating_points:
            point = np.divide(point, self.operating_points_scale)
            var += 1/(2*(distance.euclidean(point, X)))
        return var

    def add_unfeasible_point(self, X):
        if X not in self.unfeasible_operating_points:
            self.unfeasible_operating_points.append(X)
            self.number_of_unfeasible_points += 1
            scale = [0,0,0]
            for point in self.unfeasible_operating_points:
                scale[0] += point[0]
                scale[1] += point[1]
                scale[2] += point[2]
            self.operating_points_scale = scale/self.number_of_unfeasible_points

    # Calculates the total loss of the converter, and it's efficiency.
    # Compensates for the fact that some losses depend of the input current.
    def compensated_total_loss(self, X, activation_table=True, override=False):
        if np.prod(X == self.last_calculated_operating_point, dtype=bool) and not override:
            return self.last_calculated_loss+self.unfeasible_points_barrier(X)
        else:
            feasible = self.simulate_efficiency_independent_variables(X)
            efficiency = 0.8
            loss = self.design_features['Po'] * (1 - efficiency) / efficiency
            error = 2
            while error > 0.01:
                loss_last = loss
                loss = self.total_loss(X, efficiency)
                efficiency = self.design_features['Po'] / (self.design_features['Po'] + loss)
                error = abs(loss_last - loss)
            if math.isnan(loss) or math.isinf(loss):
                return 0
            else:
                self.last_calculated_loss = loss
                self.last_calculated_efficiency = efficiency
                self.last_calculated_operating_point = X
                return loss

    # Calculates the total loss of the converter, and it's efficiency.
    # Compensates for the fact that some losses depend of the input current.
    def compensated_total_loss_with_barrier(self, X, activation_table=True, override=False):
        if np.prod(X == self.last_calculated_operating_point, dtype=bool) and not override:
            return self.last_calculated_loss+self.unfeasible_points_barrier(X)
        else:
            feasible = self.simulate_efficiency_independent_variables(X)
            if not feasible:
                self.add_unfeasible_point(X)
                return self.unfeasible_points_barrier(X)
            efficiency = 0.8
            loss = self.design_features['Po'] * (1 - efficiency) / efficiency
            error = 2
            while error > 0.01:
                loss_last = loss
                loss = self.total_loss(X, efficiency)
                efficiency = self.design_features['Po'] / (self.design_features['Po'] + loss)
                error = abs(loss_last - loss)
            if math.isnan(loss) or math.isinf(loss):
                self.add_unfeasible_point(X)
                return self.unfeasible_points_barrier(X)
            else:
                self.last_calculated_loss = loss
                self.last_calculated_efficiency = efficiency
                self.last_calculated_operating_point = X
                return loss+self.unfeasible_points_barrier(X)

    # Calculates the total loss of the converter, and it's efficiency.
    # Compensates for the fact that some losses depend of the input current.
    def compensated_total_loss_with_barrier_and_feasibility(self, X, activation_table=True, override=False):
        if np.prod(X == self.last_calculated_operating_point, dtype=bool) and not override:
            return self.last_calculated_loss+self.unfeasible_points_barrier(X)
        else:
            feasible = self.simulate_efficiency_independent_variables(X)
            if not feasible:
                self.add_unfeasible_point(X)
                return self.unfeasible_points_barrier(X), False
            efficiency = 0.8
            loss = self.design_features['Po'] * (1 - efficiency) / efficiency
            error = 2
            while error > 0.01:
                loss_last = loss
                loss = self.total_loss(X, efficiency)
                efficiency = self.design_features['Po'] / (self.design_features['Po'] + loss)
                error = abs(loss_last - loss)
            if math.isnan(loss) or math.isinf(loss):
                self.add_unfeasible_point(X)
                return self.unfeasible_points_barrier(X), False
            else:
                self.last_calculated_loss = loss
                self.last_calculated_efficiency = efficiency
                self.last_calculated_operating_point = X
                return loss+self.unfeasible_points_barrier(X), True


    # Calculates the total loss of the converter, and it's efficiency.
    # Compensates for the fact that some losses depend of the input current.
    def compensated_total_loss_with_feasibility(self, X, activation_table=True, override=False):
        if np.prod(X == self.last_calculated_operating_point, dtype=bool) and not override:
            return self.last_calculated_loss
        else:
            feasible = self.simulate_efficiency_independent_variables(X)
            if not feasible:
                return 0, False
            efficiency = 0.8
            loss = self.design_features['Po'] * (1 - efficiency) / efficiency
            error = 2
            while error > 0.01:
                loss_last = loss
                loss = self.total_loss(X, efficiency)
                efficiency = self.design_features['Po'] / (self.design_features['Po'] + loss)
                error = abs(loss_last - loss)
            if math.isnan(loss) or math.isinf(loss):
                return 0, False
            else:
                self.last_calculated_loss = loss
                self.last_calculated_efficiency = efficiency
                self.last_calculated_operating_point = X
                return loss, True

    # Calculates the total loss of the converter, and it's efficiency.
    # Compensates for the fact that some losses depend of the input current.
    def compensated_total_loss_separate(self, X, activation_table=True):
        feasible = self.simulate_efficiency_independent_variables(X)
        if not feasible:
            return None, False
        efficiency = 0.8
        total_loss = self.design_features['Po'] * (1 - efficiency) / efficiency
        error = 2
        while error > 0.01:
            loss_last = total_loss
            loss = self.total_loss_separate(X, efficiency)
            total_loss = loss['Total']
            efficiency = self.design_features['Po'] / (self.design_features['Po'] + total_loss)
            error = abs(loss_last - total_loss)
        return loss, True

    # Calculates the total loss of the converter, for a given estimated efficiency.
    def total_loss(self, X, efficiency):
        output = 0
        self.simulate_efficiency_dependent_variables(X, efficiency)
        for component in self.loss_functions:
            for loss_type in self.loss_functions[component]:
                if self.loss_functions_activation_map[component][loss_type]:
                    partial = self.loss_functions[component][loss_type](self, X)
                    output = output + partial
        return output

    # Same as 'total_loss' but returns a dictonary containing all losses.
    def total_loss_separate(self, X, efficiency):
        output = {}
        total = 0
        self.simulate_efficiency_dependent_variables(X, efficiency)
        for component in self.loss_functions:
            output[component] = {}
            for loss_type in self.loss_functions[component]:
                if self.loss_functions_activation_map[component][loss_type]:
                    partial = self.loss_functions[component][loss_type](self, X)
                    output[component][loss_type] = partial
                    total = total + partial
        output['Total'] = total
        return output


    # Calculates all constraints.
    def total_constraint(self, X, get_feasibility=False):
        constraints = []

        # Garantees that the constrains are only calculated if the circuit has been simulated.
        if not np.prod(X == self.last_calculated_operating_point, dtype=bool):
            loss, feasible = self.compensated_total_loss(X, get_feasibility=True)
        for restriction in self.restriction_functions:
            func = restriction['function']
            if not feasible:
                res = -10
            else:
                res = func(self, X)
                if math.isnan(res) or math.isinf(res):
                    res=-10
            constraints.append(res)
        return constraints, feasiblity_flag


    # Calculates all constraints and then the violation, and sums them.
    def total_violation(self, X):
        constraints, feasible = self.total_constraint(X)
        if not feasible:
            return None, False
        violation = 0
        for var in constraints:
            violation += max(0, -var)**2
        return violation, True

    'SIMULATION'
    def simulate_efficiency_independent_variables(self, X):
        fs = X[0]
        Li = X[1]
        Lk = X[2]

        self.transformer.Primary.calculate_rca(fs, 100)
        self.transformer.Secondary.calculate_rca(fs, 100)
        self.entrance_inductor.calculate_rca(fs, 40)
        self.auxiliary_inductor.calculate_rca(fs, 100)

        Ts = 1 / fs

        [Vc3, Vc4, D], feasiblity_flag_D = Functions.vc3_vc4_d(self, fs, Lk)
        Vo = Vc3 + Vc4
        Functions.vo(self, fs, Lk, D)

        calculated_values = {
            'Ts': Ts,
            'Vc3': Vc3,
            'Vc4': Vc4,
            'Vo': Vo,
            'D': D
        }

        feasibility_flag_t3_t6 = False
        if feasiblity_flag_D:
            t3, t6, feasibility_flag_t3_t6 = Functions.t3t6(self, calculated_values)

        Po = self.design_features['Po']
        Vi = self.design_features['Vi']['Nominal']
        Ro = self.design_features['Ro']
        Vc1 = Vi * D / (1 - D)
        Vc2 = Vi
        n = self.transformer.Ratio

        Ipk_pos = 2 * n * Vo / (Ro * (1-D))
        Ipk_neg = -2 * n * Vo / (Ro * D)
        Ipk_pos_1 = 2 * n * Ts * Vo / (Ro * (Ts + t3 - t6))
        Ipk_neg_1 = 2 * n * Ts * Vo / (Ro * (t3 - t6))

        dIin = Vi * D * Ts / Li
        
        Io = Po / Vo
        dBLi = Li*dIin/(self.entrance_inductor.N*self.entrance_inductor.Core.Ae)

        aux = {
            't3': t3,
            't6': t6,
            'Ro': Ro,
            'Vc1': Vc1,
            'Vc2': Vc2,
            'Ipk_pos': Ipk_pos,
            'Ipk_neg': Ipk_neg,
            'Ipk_pos_1': Ipk_pos_1,
            'Ipk_neg_1': Ipk_neg_1,
            'Li': Li,
            'Lk': Lk,
            'Io': Io,
            'dBLi': dBLi,
            'dIin': dIin
        }
        calculated_values.update(aux)

        # Not efficiency dependent.
        LkVrms = Functions.AuxiliaryInductorVrms(self, calculated_values)
        calculated_values['TransformerIrms'] = Functions.TransformerIRms(self, calculated_values)[0]
        calculated_values['D3Iavg'] = Functions.D3Iavg(self, calculated_values)
        calculated_values['D3Irms'] = Functions.D3Irms(self, calculated_values)
        calculated_values['D4Iavg'] = Functions.D4Iavg(self, calculated_values)
        calculated_values['D4Irms'] = Functions.D4Irms(self, calculated_values)
        calculated_values['C3Irms'] = Functions.C3Irms(self, calculated_values)
        calculated_values['C4Irms'] = Functions.C4Irms(self, calculated_values)
        calculated_values['TransformerHarmonics'] = Functions.TransformerCurrentHarmonics(self, calculated_values)
        calculated_values['LkVrms'] = LkVrms
        calculated_values['BmaxLk'] = LkVrms/(self.auxiliary_inductor.Core.Ae*fs*7*self.auxiliary_inductor.N)

        self.calculated_values = calculated_values
        return (feasiblity_flag_D and feasibility_flag_t3_t6)

    def simulate_efficiency_dependent_variables(self, X, efficiency):
        
        Li = X[1]
        Iin = (self.design_features['Po'] / (self.design_features['Vi']['Nominal']*efficiency))
        dIin = self.calculated_values['dIin']
        Ipk_pos = self.calculated_values['Ipk_pos']
        Ipk_neg = self.calculated_values['Ipk_neg']
        Ipk = Iin + (dIin / 2)
        Imin = Iin - (dIin / 2)
        Is1max = Ipk_pos - Imin
        Is2max = Ipk - Ipk_neg
        BmaxLi = Li*Ipk/(self.entrance_inductor.N*self.entrance_inductor.Core.Ae)
        aux = {
            'Ipk': Ipk,
            'Imin': Imin,
            'Iin': Iin,
            'BmaxLi': BmaxLi,
            'dIin': dIin,
            'Is1max': Is1max,
            'Is2max': Is2max
        }
        self.calculated_values.update(aux)
        self.calculated_values['C1Irms'] = Functions.c1_irms(self, self.calculated_values)
        self.calculated_values['C2Irms'] = Functions.c2_irms(self, self.calculated_values)
        self.calculated_values['S1Irms'] = Functions.s1_irms(self, self.calculated_values)
        self.calculated_values['S2Irms'] = Functions.s2_irms(self, self.calculated_values)
        self.calculated_values['EntranceInductorHarmonics'] = Functions.InputCurrentHarmonics(self, self.calculated_values)
        self.calculated_values['LiIrms'] = Functions.LiIrms(self, self.calculated_values)

    'AUXILIARY'
    def summarize(self):
        print("\n")
        print("Resumo do Conversor\n")
        print("Transformador")
        print("- Espiras [{},{}]".format(self.transformer.Primary.N, self.transformer.Secondary.N))
        print("- Condutores [{},{}]".format(self.transformer.Primary.Ncond, self.transformer.Secondary.Ncond))
        print("- Cabo [{},{}]".format(self.transformer.Primary.Cable.Name, self.transformer.Secondary.Cable.Name))
        print("- Núcleo {}".format(self.transformer.Core.Name))
        print("Indutor de Entrada")
        print("- Espiras {}".format(self.entrance_inductor.N))
        print("- Condutores {}".format(self.entrance_inductor.Ncond))
        print("- Cabo {}".format(self.entrance_inductor.Cable.Name))
        print("- Núcleo {}".format(self.entrance_inductor.Core.Name))
        print("Indutor Auxiliar")
        print("- Espiras {}".format(self.auxiliary_inductor.N))
        print("- Condutores {}".format(self.auxiliary_inductor.Ncond))
        print("- Cabo {}".format(self.auxiliary_inductor.Cable.Name))
        print("- Núcleo {}".format(self.auxiliary_inductor.Core.Name))
        print("Chaves")
        print("-S1 - {}".format(self.switches[0].Name))
        print("-S2 - {}".format(self.switches[1].Name))
        print("Capacitores")
        print("-C1 - {}".format(self.capacitors[0].Name))
        print("-C2 - {}".format(self.capacitors[1].Name))
        print("-C3 - {}".format(self.capacitors[2].Name))
        print("-C4 - {}".format(self.capacitors[3].Name))
        print("Diodos")
        print("-D3 - {}".format(self.diodes[0].Name))
        print("-D4 - {}".format(self.diodes[1].Name))

    def get_parameter(self, name):
        if name == 'primary_cable':
            return self.transformer.Primary.Cable                       # ok
        elif name == 'secondary_cable':
            return self.transformer.Secondary.Cable                     # ok
        elif name == 'transformer_core':
            return self.transformer.Core                                # ok
        elif name == 'primary_winding':
            return self.transformer.Primary.N                           # ok
        elif name == 'secondary_winding':
            return self.transformer.Secondary.N                         # ok
        elif name == 'primary_parallel_wires':
            return self.transformer.Primary.Ncond                       # ok
        elif name == 'secondary_parallel_wires':
            return self.transformer.Secondary.Ncond                     # ok
        elif name == 'entrance_inductor_cable':
            return self.entrance_inductor.Cable                          # ok
        elif name == 'entrance_inductor_winding':
            return self.entrance_inductor.N                              # ok
        elif name == 'entrance_inductor_parallel_wires':
            return self.entrance_inductor.Ncond                          # ok
        elif name == 'entrance_inductor_core':
            return self.entrance_inductor.Core                           # ok
        elif name == 'auxiliary_inductor_cable':
            return self.auxiliary_inductor.Cable                         # ok
        elif name == 'auxiliary_inductor_winding':
            return self.auxiliary_inductor.N                             # ok
        elif name == 'auxiliary_inductor_parallel_wires':
            return self.auxiliary_inductor.Ncond                         # ok
        elif name == 'auxiliary_inductor_core':
            return self.auxiliary_inductor.Core                          # ok
        elif name == 'c1' or name == 'C1':
            return self.Capacitors[0]                                   # ok
        elif name == 'c2' or name == 'C2':
            return self.Capacitors[1]                                   # ok
        elif name == 'c3' or name == 'C3':
            return self.Capacitors[2]                                   # ok
        elif name == 'c4' or name == 'C4':
            return self.Capacitors[3]                                   # ok
        elif name == 'd3' or name == 'D3':
            return self.Diodes[0]                                       # ok
        elif name == 'd4' or name == 'D4':
            return self.Diodes[1]                                       # ok
        elif name == 's1' or name == 'S1':
            return self.Switches[0]                                     # ok
        elif name == 'S2' or name == 'S2':
            return self.Switches[1]                                     # ok
        else:
            raise Exception(name + " is not a defined parameter")

    def set_parameter(self, name, value):
        if name == 'primary_cable':
            self.transformer.Primary.Cable = value
        elif name == 'secondary_cable':
            self.transformer.Secondary.Cable = value
        elif name == 'transformer_core':
            self.transformer.Core = value
        elif name == 'primary_winding':
            self.transformer.Primary.N = value
        elif name == 'secondary_winding':
            self.transformer.Secondary.N = value
        elif name == 'primary_parallel_wires':
            self.transformer.Primary.Ncond = value
        elif name == 'secondary_parallel_wires':
            self.transformer.Secondary.Ncond = value
        elif name == 'entrance_inductor_cable':
            self.entrance_inductor.Cable = value
        elif name == 'entrance_inductor_winding':
            self.entrance_inductor.N = value
        elif name == 'entrance_inductor_parallel_wires':
            self.entrance_inductor.Ncond = value
        elif name == 'entrance_inductor_core':
            self.entrance_inductor.Core = value
        elif name == 'auxiliary_inductor_cable':
            self.auxiliary_inductor.Cable = value
        elif name == 'auxiliary_inductor_winding':
            self.auxiliary_inductor.N = value
        elif name == 'auxiliary_inductor_parallel_wires':
            self.auxiliary_inductor.Ncond = value
        elif name == 'auxiliary_inductor_core':
            self.auxiliary_inductor.Core = value
        elif name == 'c1' or name == 'C1':
            self.Capacitors[0] = value
        elif name == 'c2' or name == 'C2':
            self.Capacitors[1] = value
        elif name == 'c3' or name == 'C3':
            self.Capacitors[2] = value
        elif name == 'c4' or name == 'C4':
            self.Capacitors[3] = value
        elif name == 'd3' or name == 'D3':
            self.Diodes[0] = value
        elif name == 'd4' or name == 'D4':
            self.Diodes[1] = value
        elif name == 's1' or name == 'S1':
            self.Switches[0] = value
        elif name == 'S2' or name == 'S2':
            self.Switches[1] = value
        else:
            raise Exception(name + " is not a defined parameter")

    def get_simulated_values(self):
        return self.calculated_values