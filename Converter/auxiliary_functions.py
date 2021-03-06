import numpy as np
from scipy.optimize import fsolve, root, minimize
import datetime
from Converter.fqs import *

# Calcula Vc3, Vc4 e a razão cíclica necessária para obter o valor de Vo desejado.
def vc3_vc4_d(obj, fs, Lk):
    start = datetime.datetime.now()
    k = 2*fs*Lk*obj.transformer.Ratio**2/obj.design_features['Ro']
    b = -obj.design_features['D']['Expected'] - 1
    c = 2*k + obj.design_features['D']['Expected']
    d = -2*k
    e = k


    Dlist = single_quartic(1,b,c,d,e)
    Found = False
    for D in Dlist:
        if D.imag == 0:
            if 0.3 <= D.real <= 0.7:
                Dinitial = D.real
                Found = True

    if Found:
        x0 = [obj.design_features['Vo'] - obj.transformer.Ratio*obj.design_features['Vi']['Nominal'] - 1, obj.transformer.Ratio*obj.design_features['Vi']['Nominal'] - 1, Dinitial]
        k1 = obj.design_features['Ro'] / (2 * Lk * fs* obj.design_features['Vi']['Nominal'] * (obj.transformer.Ratio ** 3))
        k2 = obj.transformer.Ratio * obj.design_features['Vi']['Nominal']
        solution = fsolve(fvo, x0, args=(k1, k2, obj.design_features['Vo']))

    return solution, Found

# Sistema de equações para obter Vc3, Vc4 e D.
def fvo(X, k1, k2, Vo):
    Vc3 = X[0]
    Vc4 = X[1]
    D = X[2]
    return np.array([Vo + k1 * (Vc3 ** 2) * (Vc4 - k2) * (Vc4 * (1 - D) + D * k2)/(Vo**2), Vo + k1 * (Vc4 ** 2) * (Vc3 + k2) * (Vc3 * (1 - D) - D * k2)/(Vo**2), Vc3 + Vc4 - Vo])

# Calcula Vo, utilizando a formula aproximada. Função apenas de teste.
def vo(obj, fs, Lk, D):
    Vi = obj.design_features['Vi']['Nominal']
    n = obj.transformer.Ratio
    Ro = obj.design_features['Ro']
    
    Vo = Vi*n*Ro*D**2*(1-D)/(n**2*Lk*fs*((2*D-1)**2+1) + D**2*Ro*(1-D)**2)
    return Vo

# Calcula t3 e t6.
def t3t6(obj, values, case='Nominal'):
    Ts = values['Ts']
    Vc3 = values['Vc3']
    Vc4 = values['Vc4']
    Vo = values['Vo']

    D = values['D']
    Vi = obj.design_features['Vi'][case]

    n = obj.transformer.Ratio

    t3 = Ts * Vc4 * (Vc3 * (D - 1) + Vi * D * n) / (Vi * n * Vo)
    t6 = Ts * (Vi * (Vc4 * D + Vc3)*n + (D - 1) * Vc3 * Vc4) / (Vi * n * Vo)
    feasible_flag = False
    if 0 <= t3 <= values['Ts'] and 0 < t6 <= values['Ts']:
        feasible_flag = True

    return t3, t6, feasible_flag

'EQUAÇÕES DE TENSÃO E CORRENTE DOS COMPONENTES'
def TransformerIRms(obj, values):
    Ts = values['Ts']
    Vc3 = values['Vc3']
    Vc4 = values['Vc4']
    t3 = values['t3']
    t6 = values['t6']
    Vc1 = values['Vc1']
    Vc2 = values['Vc2']
    Ipk_pos_1 = values['Ipk_pos_1']
    Ipk_neg_1 = values['Ipk_neg_1']


    D = values['D']
    n = obj.transformer.Ratio
    Lk = values['Lk']

    Ip_rms = t3*Ipk_pos_1**2 - (t3**2)*Ipk_pos_1*((Vc2 + Vc3/n)/Lk) + ((t3**3)/3)*((Vc2 + Vc3/n)/Lk)**2
    Ip_rms = Ip_rms + (((D*Ts)**3)/3)*((Vc4/n - Vc2)/Lk)**2
    Ip_rms = Ip_rms + (t6-D*Ts)*Ipk_neg_1**2 + ((t6-D*Ts)**2)*((Vc4/n + Vc1)/Lk) + (((t6-D*Ts)**3)/3)*((Vc4/n + Vc1)/Lk)**2
    Ip_rms = Ip_rms + (((Ts-t6)**3)/3)*((Vc1 - Vc3/n)/Lk)**2
    Ip_rms = np.sqrt(Ip_rms/Ts)
    Is_rms = Ip_rms/n
    return [Ip_rms, Is_rms]


def AuxiliaryInductorVrms(obj, values):
    Ts = values['Ts']
    Vc3 = values['Vc3']
    Vc4 = values['Vc4']
    t3 = values['t3']
    t6 = values['t6']
    Vc1 = values['Vc1']
    Vc2 = values['Vc2']

    D = values['D']
    n = obj.transformer.Ratio
    b = [0, 0, 0, 0]
    a = [- (Vc2 + Vc3 / n), (Vc4 / n - Vc2), (Vc4 / n + Vc1), (Vc1 - Vc3 / n)]
    tf = [t3, D * Ts, t6, Ts]
    ti = [0, t3, D * Ts, t6]
    return rms_piecewise_linear(a, b, ti, tf, Ts)


def TransformerPrimaryCurrentHarmonics(obj, values):
    Ts = values['Ts']
    Vc3 = values['Vc3']
    Vc4 = values['Vc4']
    t3 = values['t3']
    t6 = values['t6']
    Vc1 = values['Vc1']
    Vc2 = values['Vc2']
    Ipk_pos_1 = values['Ipk_pos_1']
    Ipk_neg_1 = values['Ipk_neg_1']

    D = values['D']
    n = obj.transformer.Ratio
    Lk = values['Lk']

    A = [Ipk_pos_1, 0, Ipk_neg_1, 0]
    B = [- (Vc2 + Vc3 / n) / Lk, (Vc4 / n - Vc2) / Lk, (Vc4 / n + Vc1) / Lk, (Vc1 - Vc3 / n) / Lk]
    Tf = [t3, D * Ts, t6, Ts]
    Ti = [0, t3, D*Ts, t6]

    harmonics = fourier_piecewise_linear(A, B, Ti, Tf, 1/Ts, 40)
    return harmonics

def TransformerCurrentHarmonics(obj, values):
    Ts = values['Ts']
    Vc3 = values['Vc3']
    Vc4 = values['Vc4']
    t3 = values['t3']
    t6 = values['t6']
    Vc1 = values['Vc1']
    Vc2 = values['Vc2']
    Ipk_pos_1 = values['Ipk_pos_1']
    Ipk_neg_1 = values['Ipk_neg_1']

    D = values['D']
    n = obj.transformer.Ratio
    Lk = values['Lk']

    A = [Ipk_pos_1, 0, Ipk_neg_1, 0]
    B = [- (Vc2 + Vc3 / n) / Lk, (Vc4 / n - Vc2) / Lk, (Vc4 / n + Vc1) / Lk, (Vc1 - Vc3 / n) / Lk]
    Tf = [t3, D * Ts, t6, Ts]
    Ti = [0, t3, D*Ts, t6]

    harmonics = fourier_piecewise_linear(A, B, Ti, Tf, 1/Ts, 100)
    return harmonics

def LiIrms(obj, values):
    Ts = values['Ts']
    dIin = values['dIin']
    Imax = values['Ipk']
    Imin = values['Imin']

    D = values['D']
    A = [Imin, Imax]
    B = [dIin, -dIin]
    Tf = [D*Ts, Ts]
    Ti = [0, D*Ts]

    harmonics = rms_piecewise_linear(A, B, Ti, Tf, Ts)
    return harmonics


def InputCurrentHarmonics(obj, values):
    Ts = values['Ts']
    dIin = values['dIin']
    Imax = values['Ipk']
    Imin = values['Imin']

    D = values['D']
    A = [Imin, Imax]
    B = [dIin, -dIin]
    Tf = [D*Ts, Ts]
    Ti = [0, D*Ts]

    harmonics = fourier_piecewise_linear(A, B, Ti, Tf, 1 / Ts, 40)
    return harmonics


def c1_irms(obj, values):
    Ts = values['Ts']
    Vc3 = values['Vc3']
    Vc4 = values['Vc4']
    t6 = values['t6']
    Ipk_neg_1 = values['Ipk_neg_1']
    Ipk = values['Ipk']
    Li = values['Li']

    D = values['D']
    Vi = obj.design_features['Vi']['Nominal']
    n = obj.transformer.Ratio
    Lk = values['Lk']
    dt1 = t6 - D * Ts
    dt2 = Ts - t6
    Vterm1 = Vi * D / (1 - D)

    Ic1_rms = dt1*(Ipk - Ipk_neg_1)**2 - (dt1**2)*(Ipk - Ipk_neg_1)*(Vterm1/Li + (Vc4/n + Vterm1)/Lk) + (dt1**3)*((Vterm1/Li + (Vc4/n + Vterm1)/Lk)**2)/3
    Ic1_rms = Ic1_rms + dt2*Ipk**2 - (dt2**2)*Ipk*(Vterm1/Li + (Vterm1 - Vc3/n)/Lk) + (dt2**3)*((Vterm1/Li + (Vterm1 - Vc3/n)/Lk)**2)/3
    Ic1_rms = np.sqrt(Ic1_rms/Ts)
    return Ic1_rms


def c2_irms(obj, values):
    Ts = values['Ts']
    Vc1 = values['Vc1']
    Vc2 = values['Vc2']
    Vc3 = values['Vc3']
    Vc4 = values['Vc4']
    t3 = values['t3']
    t6 = values['t6']
    Ipk_pos_1 = values['Ipk_pos_1']
    Ipk = values['Ipk']
    Li = values['Li']

    D = values['D']
    Vi = obj.design_features['Vi']['Nominal']
    n = obj.transformer.Ratio
    Lk = values['Lk']
    dt2 = (D * Ts - t3)
    dt3 = t6 - D*Ts
    dt4 = Ts - t6

    term1 = (Vc3/n + Vc2)/Lk
    term2 = (Vc4/n - Vc2)/Lk
    term3 = (Vi - (Vc1 + Vc2))/Li

    # Primeira parte da integral.
    Ic2_rms = t3*(Ipk_pos_1**2) - (t3**2)*Ipk_pos_1*term1 + (t3**3)*(term1**2)/3
    Ic2_rms = Ic2_rms + (dt2**3)*(term2**2)/3
    Ic2_rms = Ic2_rms + (dt4+dt3)*Ipk**2 + Ipk*term3*(dt3**2 + dt4**2) + ((dt3**3 + dt4**3)/3)*term3**2
    Ic2_rms = np.sqrt(Ic2_rms/Ts)
    return Ic2_rms


def s1_irms(obj, values):
    Ts = values['Ts']
    Vc3 = values['Vc3']
    Vc4 = values['Vc4']
    t6 = values['t6']
    Ipk_neg_1 = values['Ipk_neg_1']
    Ipk = values['Ipk']
    Li = values['Li']

    D = values['D']
    Vi = obj.design_features['Vi']['Nominal']
    n = obj.transformer.Ratio
    Lk = values['Lk']

    Vterm1 = Vi * D / (1 - D)
    Is1_rms = (t6-D*Ts)*(Ipk_neg_1-Ipk)**2 + ((t6-D*Ts)**2)*(Ipk_neg_1-Ipk)*((Vc4/n + Vterm1)/Lk + Vterm1/Li)
    Is1_rms = Is1_rms + ((t6-D*Ts)**3)*(((Vc4/n + Vterm1)/Lk + Vterm1/Li)**2)/3
    Is1_rms = Is1_rms + (Ts - t6)*(Ipk**2) - ((Ts - t6)**2)*Ipk*((Vterm1 - Vc3/n)/Lk + Vterm1/Li)
    Is1_rms = Is1_rms + ((Ts - t6)**3)*(((Vterm1 - Vc3/n)/Lk + Vterm1/Li)**2)/3
    Is1_rms = np.sqrt(Is1_rms/Ts)
    return Is1_rms


def s2_irms(obj, values):
    Ts = values['Ts']
    Vc3 = values['Vc3']
    Vc4 = values['Vc4']
    t3 = values['t3']
    Ipk_pos_1 = values['Ipk_pos_1']
    Imin = values['Imin']
    Li = values['Li']

    D = values['D']
    Vi = obj.design_features['Vi']['Nominal']
    n = obj.transformer.Ratio
    Lk = values['Lk']

    Is2_rms = t3*(Imin - Ipk_pos_1)**2 + (t3**2)*(Imin - Ipk_pos_1)*(Vi/Li + (Vi + Vc3/n)/Lk)
    Is2_rms = Is2_rms + ((t3**3)/3)*(Vi/Li + (Vi + Vc3/n)/Lk)**2
    Is2_rms = Is2_rms + (D*Ts - t3)*Imin**2 + ((D*Ts - t3)**2)*(Vi/Li - (Vc4/n - Vi)/Lk)
    Is2_rms = Is2_rms + (((D*Ts - t3)**3)/3)*(Vi/Li - (Vc4/n - Vi)/Lk)**2
    Is2_rms = np.sqrt(Is2_rms/Ts)
    return Is2_rms


def D3Iavg(obj, values):
    Ts = values['Ts']
    Vc3 = values['Vc3']
    t3 = values['t3']
    t6 = values['t6']
    Ipk_pos_1 = values['Ipk_pos_1']

    D = values['D']
    Vi = obj.design_features['Vi']['Nominal']
    n = obj.transformer.Ratio
    Lk = values['Lk']

    Id3_avg = t3*(Ipk_pos_1/n) - (t3**2)*(Vi + Vc3/n)/(2*n*Lk)
    Id3_avg = Id3_avg + (Vi*D/(1-D) - Vc3/n)*((Ts-t6)**2)/(2*n*Lk)
    Id3_avg = Id3_avg/Ts
    return Id3_avg


def D3Irms(obj, values):
    Ts = values['Ts']
    Vc3 = values['Vc3']
    t3 = values['t3']
    t6 = values['t6']
    Ipk_pos_1 = values['Ipk_pos_1']

    D = values['D']
    Vi = obj.design_features['Vi']['Nominal']
    n = obj.transformer.Ratio
    Lk = values['Lk']

    Id3_rms = t3*(Ipk_pos_1/n)**2 - ((t3/n)**2)*Ipk_pos_1*(Vi + Vc3/n)/Lk + (t3**3)*(((Vi + Vc3/n)/(n*Lk))**2)/3
    Id3_rms = Id3_rms + ((Ts-t6)**3)*(((Vi*D/(1-D) - Vc3/n)/(n*Lk))**2)/3
    Id3_rms = np.sqrt(Id3_rms/Ts)
    return Id3_rms


def D4Iavg(obj, values):
    Ts = values['Ts']
    Vc4 = values['Vc4']
    t3 = values['t3']
    t6 = values['t6']
    Ipk_neg_1 = values['Ipk_neg_1']

    D = values['D']
    Vi = obj.design_features['Vi']['Nominal']
    n = obj.transformer.Ratio
    Lk = values['Lk']

    Id4_avg = -(t6-D*Ts)*(Ipk_neg_1/n) - ((t6-D*Ts)**2)*(Vi*D/(1-D) + Vc4/n)/(2*n*Lk)
    Id4_avg = Id4_avg - (-Vi + Vc4/n)*((D*Ts-t3)**2)/(2*n*Lk)
    Id4_avg = Id4_avg/Ts
    return Id4_avg


def D4Irms(obj, values):
    Ts = values['Ts']
    Vc4 = values['Vc4']
    t3 = values['t3']
    t6 = values['t6']
    Ipk_neg_1 = values['Ipk_neg_1']

    D = values['D']
    Vi = obj.design_features['Vi']['Nominal']
    n = obj.transformer.Ratio
    Lk = values['Lk']

    Id4_rms = ((D*Ts-t3)**3)*(((Vc4/n - Vi)/(Lk*n))**2)/3 + (t6-D*Ts)*(Ipk_neg_1/n)**2
    Id4_rms = Id4_rms + (Ipk_neg_1/Lk)*(Vc4/n + Vi*D/(1-D))*((t6-D*Ts)/n)**2
    Id4_rms = Id4_rms + (((t6-D*Ts)**3)/3)*((Vc4/n + Vi*D/(1-D))/(n*Lk))**2
    Id4_rms = np.sqrt(Id4_rms/Ts)
    return Id4_rms


def C3Irms(obj, values):
    Ts = values['Ts']
    Vc3 = values['Vc3']
    t3 = values['t3']
    t6 = values['t6']
    Ipk_pos_1 = values['Ipk_pos_1']
    Io = values['Io']

    D = values['D']
    Vi = obj.design_features['Vi']['Nominal']
    n = obj.transformer.Ratio
    Lk = values['Lk']

    Ic3_rms = t3*(Ipk_pos_1/n - Io)**2 - (t3**2)*(Ipk_pos_1/n - Io)*((Vi + Vc3/n)/(n*Lk))
    Ic3_rms = Ic3_rms + (t3**3)*(((Vi + Vc3/n)/(n*Lk))**2)/3
    Ic3_rms = Ic3_rms + (Ts - t3)*Io**2 - (Io/(n*Lk))*(Vi*D/(1-D) - Vc3/n)*(Ts - t6)**2
    Ic3_rms = Ic3_rms + ((Ts-t6)**3)*(((Vi*D/(1-D) - Vc3/n)/(n*Lk))**2)/3
    Ic3_rms = np.sqrt(Ic3_rms/Ts)
    return Ic3_rms


def C4Irms(obj, values):
    Ts = values['Ts']
    Vc4 = values['Vc4']
    t3 = values['t3']
    t6 = values['t6']
    Ipk_neg_1 = values['Ipk_neg_1']
    Io = values['Io']

    D = values['D']
    Vi = obj.design_features['Vi']['Nominal']
    n = obj.transformer.Ratio
    Lk = values['Lk']

    Ic4_rms = (Ts*(1+D) - t6)*Io**2 + Io*((Vc4/n - Vi)/(n*Lk))*(D*Ts-t3)**2
    Ic4_rms = Ic4_rms + ((D*Ts-t3)**3)*(((Vc4/n - Vi)/(n*Lk))**2)/3
    Ic4_rms = Ic4_rms + (t6-D*Ts)*(Io + Ipk_neg_1/n)**2
    Ic4_rms = Ic4_rms + ((t6-D*Ts)**2)*(Io + Ipk_neg_1/n)*((Vc4/n + Vi*D/(1-D))/(n*Lk))
    Ic4_rms = Ic4_rms + ((t6-D*Ts)**3)*(((Vc4/n + Vi*D/(1-D))/(n*Lk))**2)/3
    Ic4_rms = np.sqrt(Ic4_rms/Ts)
    return Ic4_rms

# Função que calcula a série de fourier de uma função consistente apenas de segmentos de reta.
def fourier_piecewise_linear(A, B, Ti, Tf, fo, noc):
    harmonic_amplitudes = np.zeros(noc)
    base = 2 * np.pi * fo
    for n in range(0, noc):
        term = base*n
        an = 0
        bn = 0
        if n == 0:
            for [a, b, ti, tf] in zip(A, B, Ti, Tf):
                an += (a-b*ti)*(tf-ti) + (b/2)*(tf**2 - ti**2)
            cn = an*fo
        else:
            for [a, b, ti, tf] in zip(A, B, Ti, Tf):
                costi = np.cos(term*ti)
                costf = np.cos(term*tf)
                sinti = np.sin(term*ti)
                sintf = np.sin(term*tf)
                an += ((sintf - sinti)*a + b*(tf-ti)*sintf + (b*(costf - costi)/term))/term
                bn += ((costi - costf)*a - b*(tf-ti)*costf + (b*(sintf - sinti)/term))/term
            cn = np.sqrt(an**2 + bn**2)*2*fo
        harmonic_amplitudes[n] = cn
    return harmonic_amplitudes

# Função que calcula o valor RMS de uma função consistente apenas de segmentos de reta.
def rms_piecewise_linear(A, B, Ti, Tf, Ts):
    rms = 0
    for [a, b, ti, tf] in zip(A, B, Ti, Tf):
        rms += (tf - ti)*(a - b*ti)**2 + (tf**2 - ti**2)*(a-b*ti)*b + (tf**3 - ti**3)*(b**2)/3
    rms = np.sqrt(rms/Ts)
    return rms


# def iZVS2(obj, f, Li):
#     Po = obj.design_features['Po']
#     Vo = obj.design_features['Vo']
#     Ro = obj.design_features['Ro']


#     return 2*obj.transformer.Ratio*Vo/(Ro*(1-Dmin)) - (Po/(2*Vmax)) + (Vmax*Dmin)/(2*Li_lower_bound*frequency_upper_bound)


'REMOVER DAQUI'
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