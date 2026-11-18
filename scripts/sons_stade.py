#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sons_stade.py — la bande-son « stade » de la vidéo du jour en 3D (paquet 277, 18/11/2026), en STÉRÉO.

Tout est fabriqué ici (numpy, scipy) : aucun enregistrement, aucune musique d'autrui.
  — le public : brouhaha de milliers de voix (bruits filtrés modulés au rythme de la parole), applaudissements
    (des milliers de claquements), « ooooh » quand l'échange s'allonge, ovation sur les grands points ;
  — le court : « pock » de la raquette (plus fort au service), rebonds, filet, crissement des semelles sur le dur,
    placés à gauche ou à droite selon l'image ;
  — l'habillage : souffle des transitions, impact du face-à-face, jingles télé courts, nappe musicale en ouverture
    et en fin ;
  — la voix de l'arbitre (synthèse vocale, scripts/voix.py) passée dans la sono du stade ; le public baisse quand
    elle parle ;
  — une réverbération de grande salle sur le tout, puis un limiteur.
Repli : si numpy ou scipy manque, scripts/video_simulation.py garde la bande-son de scripts/sons.py.
"""
import numpy as np
from scipy import signal
from scipy.io import wavfile

TAUX = 48000


def _rng(graine):
    return np.random.default_rng(graine)


def _bande(x, bas=None, haut=None, ordre=2):
    if bas and haut:
        sos = signal.butter(ordre, [bas, haut], 'bandpass', fs=TAUX, output='sos')
    elif bas:
        sos = signal.butter(ordre, bas, 'highpass', fs=TAUX, output='sos')
    else:
        sos = signal.butter(ordre, haut, 'lowpass', fs=TAUX, output='sos')
    return signal.sosfilt(sos, x, axis=0)


def _env(n, attaque, chute):
    t = np.arange(n) / TAUX
    return np.minimum(1.0, t / max(attaque, 1e-4)) * np.exp(-np.maximum(0, t - attaque) / max(chute, 1e-4))


def _st(x, pan=0.0):
    """Mono → stéréo, panoramique à puissance constante (pan −1 gauche … +1 droite)."""
    a = (pan + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], axis=1)


def _lisse(n, freq, r):
    """Enveloppe aléatoire lisse (bruit basse fréquence), entre 0 et 1."""
    pas = max(1, int(TAUX / freq))
    k = r.random(n // pas + 3)
    return np.interp(np.arange(n), np.arange(len(k)) * pas, k)


# ── le court ────────────────────────────────────────────────────────────────────────────────────────────────
def pock(fort=1.0, r=None):
    r = r or _rng(1)
    n = int(0.12 * TAUX)
    t = np.arange(n) / TAUX
    clic = _bande(r.standard_normal(n), 1800, None) * np.exp(-t / 0.0025)
    f = r.uniform(1050, 1350) * (1.08 if fort > 1 else 1)
    corde = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.018)
    corps = np.sin(2 * np.pi * r.uniform(170, 220) * t) * np.exp(-t / 0.03)
    return fort * (0.5 * clic + 0.42 * corde + 0.35 * corps)


def rebond(r=None):
    r = r or _rng(2)
    n = int(0.09 * TAUX)
    t = np.arange(n) / TAUX
    return 0.22 * (np.sin(2 * np.pi * r.uniform(160, 230) * t) * np.exp(-t / 0.02) + 0.5 * _bande(r.standard_normal(n), 900, 4000) * np.exp(-t / 0.004))


def filet(r=None):
    r = r or _rng(3)
    n = int(0.4 * TAUX)
    t = np.arange(n) / TAUX
    return 0.45 * (np.sin(2 * np.pi * 85 * t) * np.exp(-t / 0.06) + 0.6 * _bande(r.standard_normal(n), 200, 1500) * np.exp(-t / 0.09))


def crisse(r=None):
    r = r or _rng(4)
    n = int(r.uniform(0.07, 0.13) * TAUX)
    t = np.arange(n) / TAUX
    f = np.linspace(r.uniform(2100, 2600), r.uniform(2900, 3600), n) + 120 * np.sin(2 * np.pi * 38 * t)
    ph = 2 * np.cumsum(np.pi * f / TAUX)
    return 0.07 * np.sin(ph) * np.abs(np.sin(np.pi * t / t[-1])) ** 0.6


# ── le public ───────────────────────────────────────────────────────────────────────────────────────────────
def brouhaha(duree, r=None, niveau=0.06):
    """Milliers de conversations : bandes de bruit modulées au rythme de la parole (3–7 Hz), en stéréo."""
    r = r or _rng(5)
    n = int(duree * TAUX)
    out = np.zeros((n, 2))
    for k in range(8):
        voix = _bande(r.standard_normal(n), r.uniform(250, 500), r.uniform(1400, 2600))
        mod = _lisse(n, r.uniform(3, 7), r) ** 2
        out += _st(voix * mod, r.uniform(-0.9, 0.9))
    out += _st(_bande(r.standard_normal(n), 80, 600), 0) * 0.5
    fondu = int(1.0 * TAUX)
    rampe = np.minimum(1, np.minimum(np.arange(n), n - 1 - np.arange(n)) / fondu)
    return niveau * out / (np.abs(out).max() + 1e-9) * 3 * rampe[:, None]


def applaudir(duree=2.6, densite=900, vol=0.5, r=None):
    """Applaudissements : chaque claquement est un éclat de bruit de 6–12 ms, placé au hasard dans la salle."""
    r = r or _rng(6)
    n = int(duree * TAUX)
    out = np.zeros((n, 2))
    nb = int(densite * duree)
    temps = (r.beta(1.3, 2.6, nb) * n).astype(int)
    lg = int(0.012 * TAUX)
    gabarit = _bande(r.standard_normal((16, lg)).T, 900, 5200).T * np.exp(-np.arange(lg) / (0.0022 * TAUX))
    for k, d0 in enumerate(temps):
        c = gabarit[k % 16] * r.uniform(0.3, 1.0)
        fin = min(n, d0 + lg)
        p = r.uniform(-1, 1)
        out[d0:fin] += _st(c[:fin - d0], p)
    env = np.minimum(1, np.arange(n) / (0.15 * TAUX))[:, None]
    return vol * env * out / (np.abs(out).max() + 1e-9)


def clameur(duree=3.0, vol=0.4, r=None, voyelle=(700, 1150)):
    """Cris du public : bruit passé dans deux formants (une voyelle), qui gonfle puis retombe."""
    r = r or _rng(7)
    n = int(duree * TAUX)
    b = r.standard_normal((n, 2))
    x = _bande(b, voyelle[0] * 0.8, voyelle[0] * 1.2) + 0.7 * _bande(b, voyelle[1] * 0.85, voyelle[1] * 1.15)
    t = np.arange(n) / n
    env = (np.minimum(1, t / 0.18) * (1 - t) ** 1.3)[:, None]
    return vol * env * x / (np.abs(x).max() + 1e-9)


def houle(r=None):
    """« Ooooh » : le public retient son souffle quand l'échange dure."""
    r = r or _rng(8)
    n = int(1.8 * TAUX)
    t = np.arange(n) / n
    x = clameur(1.8, 0.33, r, voyelle=(380, 820))
    return x * (np.sin(np.pi * t) ** 1.5)[:, None] / (np.abs(x).max() + 1e-9) * 0.3


def ovation(duree=3.8, r=None):
    r = r or _rng(9)
    return applaudir(duree, 1900, 0.55, r) + clameur(duree, 0.32, r)


# ── l'habillage ─────────────────────────────────────────────────────────────────────────────────────────────
def souffle(duree=0.55, r=None):
    r = r or _rng(10)
    n = int(duree * TAUX)
    t = np.arange(n) / n
    x = r.standard_normal(n)
    f = 300 * (10 ** (t * 1.1))
    out = np.zeros(n)
    for k in range(0, n, 512):                                                 # filtre qui balaie (par blocs)
        sos = signal.butter(2, [max(80, f[k] * 0.7), min(18000, f[k] * 1.4)], 'bandpass', fs=TAUX, output='sos')
        out[k:k + 512] = signal.sosfilt(sos, x[k:k + 512])
    env = np.sin(np.pi * t) ** 2
    st = np.stack([out * env * (1 - t), out * env * t], axis=1)
    return 0.4 * st / (np.abs(st).max() + 1e-9)


def impact(r=None):
    r = r or _rng(11)
    n = int(1.4 * TAUX)
    t = np.arange(n) / TAUX
    f = 30 + 70 * np.exp(-t / 0.08)
    boum = np.sin(2 * np.pi * np.cumsum(f) / TAUX) * np.exp(-t / 0.45)
    return 0.8 * (boum + 0.3 * _bande(r.standard_normal(n), 2000, None) * np.exp(-t / 0.05))


def _scie(f, t):
    return 2 * ((f * t) % 1) - 1


def accord(notes, duree, vol=0.25, ouverture=1800):
    """Nappe de cuivres synthétiques (scies désaccordées, filtrées), pour les jingles."""
    n = int(duree * TAUX)
    t = np.arange(n) / TAUX
    x = sum(_scie(f * d, t) for f in notes for d in (0.997, 1.0, 1.004))
    x = _bande(x, None, ouverture, 2)
    env = np.minimum(1, t / 0.03) * np.exp(-t / (duree * 0.45))
    return vol * x * env / (np.abs(x).max() + 1e-9)


def jingle(niveau=1):
    """Annonce télé : accord qui monte (1 : balle de break / de set ; 2 : balle de match ; 3 : break, set ; 4 : fin)."""
    base = {1: [220, 277.2, 329.6], 2: [196, 246.9, 293.7, 392], 3: [261.6, 329.6, 392, 523.3], 4: [261.6, 329.6, 392, 523.3, 659.3]}[niveau]
    d = {1: 0.7, 2: 1.2, 3: 0.9, 4: 2.4}[niveau]
    a = accord(base, d, 0.22, 2400 if niveau > 2 else 1500)
    if niveau in (2, 4):
        b = impact()[:len(a)]; a = a.copy(); a[:len(b)] += b * 0.35
    return _st(a, 0)


def nappe(duree, r=None):
    """Musique d'ouverture et de fin : quatre accords lents, très doux, sous le public."""
    suite = [[220, 261.6, 329.6], [174.6, 220, 261.6], [261.6, 329.6, 392], [196, 246.9, 293.7]]
    n = int(duree * TAUX)
    out = np.zeros(n)
    d = duree / 4
    for k, ac in enumerate(suite):
        a = accord([f / 2 for f in ac] + ac, d * 1.25, 0.18, 900)
        d0 = int(k * d * TAUX)
        fin = min(n, d0 + len(a))
        out[d0:fin] += a[:fin - d0]
    t = np.arange(n) / n
    return _st(out * np.minimum(1, t / 0.08) * np.minimum(1, (1 - t) / 0.2), 0)


# ── la salle et la sono ─────────────────────────────────────────────────────────────────────────────────────
def reponse_salle(duree=1.9, r=None):
    r = r or _rng(12)
    n = int(duree * TAUX)
    t = np.arange(n) / TAUX
    ir = r.standard_normal((n, 2)) * np.exp(-t / 0.42)[:, None]
    ir = _bande(ir, None, 5000, 2)
    ir[:int(0.025 * TAUX)] = 0                                                  # pré-délai
    return ir / np.sqrt((ir ** 2).sum(axis=0))


def sono(x):
    """La voix de l'arbitre dans les haut-parleurs du stade : bande étroite, un peu saturée."""
    x = _bande(x, 280, 4800, 2)
    return np.tanh(2.2 * x / (np.abs(x).max() + 1e-9)) * 0.42


def _somme(a, b):
    n = max(len(a), len(b))
    return np.pad(a, ((0, n - len(a)), (0, 0))) + np.pad(b, ((0, n - len(b)), (0, 0)))


SONS = {
    'service': lambda r: _st(pock(1.25, r), 0), 'frappe0': lambda r: _st(pock(1.0, r), 0), 'frappe1': lambda r: _st(pock(0.8, r), 0),
    'rebond': lambda r: _st(rebond(r), 0), 'filet': lambda r: _st(filet(r), 0), 'crisse': lambda r: _st(crisse(r), 0),
    'applaudissements': lambda r: applaudir(2.6, 1000, 0.42, r), 'ovation': lambda r: ovation(3.8, r),
    'foule_entree': lambda r: ovation(4.5, r) * 0.8, 'houle': lambda r: houle(r),
    'volet': lambda r: souffle(0.55, r), 'vs': lambda r: _st(impact(r), 0),
    'annonce': lambda r: jingle(1), 'balle_match': lambda r: jingle(2), 'break': lambda r: jingle(3), 'set': lambda r: jingle(3),
    'jeu_decisif': lambda r: jingle(1), 'fin': lambda r: _somme(jingle(4), ovation(4.5, r)),
}
REVERBE = {'service': 0.25, 'frappe0': 0.25, 'frappe1': 0.25, 'rebond': 0.15, 'filet': 0.2, 'crisse': 0.15,
           'applaudissements': 0.3, 'ovation': 0.3, 'foule_entree': 0.3, 'houle': 0.35, 'voix': 0.45}


def piste(evenements, duree, chemin, voix=None, graine=7):
    """evenements : [{'t': s, 'type': nom, 'pan': −1…1, 'texte': …}] ; voix(texte) → tableau mono à TAUX ou None.
    Écrit un WAV stéréo 16 bits de `duree` secondes ; renvoie le nombre de phrases dites par l'arbitre."""
    r = _rng(graine)
    n = int(duree * TAUX)
    sec = np.zeros((n, 2))                                                      # sons secs
    hum = np.zeros((n, 2))                                                      # envoyés dans la salle
    public = brouhaha(duree, r)
    parle = np.zeros(n)
    dites = 0
    for e in sorted(evenements, key=lambda e: e['t']):
        t, nom = float(e['t']), e['type']
        if t < 0 or t >= duree:
            continue
        if nom == 'voix':
            if not voix or not e.get('texte'):
                continue
            v = voix(e['texte'])
            if v is None or not len(v):
                continue
            s = _st(sono(np.asarray(v, dtype=float)), 0)
            dites += 1
        elif nom in ('musique_intro', 'musique_fin'):
            s = nappe(float(e.get('duree') or 7.0), r)
        elif nom in SONS:
            s = SONS[nom](r)
            if nom in ('service', 'frappe0', 'frappe1', 'rebond', 'filet', 'crisse'):
                s = _st(s[:, 0] * np.sqrt(2), float(e.get('pan') or 0))
        else:
            continue
        d0 = int(t * TAUX)
        fin = min(n, d0 + len(s))
        sec[d0:fin] += s[:fin - d0]
        hum[d0:fin] += s[:fin - d0] * REVERBE.get(nom, 0.12)
        if nom == 'voix':
            parle[d0:fin] = 1
    # le public baisse quand l'arbitre parle (enveloppe lissée)
    baisse = 1 - 0.55 * signal.lfilter([0.0008], [1, -0.9992], parle)
    public *= np.clip(baisse, 0.4, 1)[:, None]
    ir = reponse_salle(1.9, r)
    salle = np.stack([signal.fftconvolve(hum[:, k] + public[:, k] * 0.25, ir[:, k])[:n] for k in (0, 1)], axis=1)
    mix = np.nan_to_num(sec + public + 0.55 * salle)
    rms = np.sqrt((mix ** 2).mean()) + 1e-9
    mix *= 0.16 / rms                                                           # niveau régulier d'une vidéo à l'autre
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)                                     # limiteur doux
    mix = np.clip(np.nan_to_num(mix), -0.98, 0.98)                            # jamais de silence par un calcul raté
    wavfile.write(chemin, TAUX, (mix * 32767).astype(np.int16))
    return dites
