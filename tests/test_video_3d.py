"""La vidéo du jour en 3D (paquet 276, 18/11/2026, Lucas : « On y va pour la vidéo du jour… se rapprocher de TopSpin…
le regarder comme un divertissement »).

Le match représentatif des simulations (le même que la vidéo 2D) est rejoué par le moteur du match ; ses moments
forts sont joués dans le stade 3D, habillage télé, son de stade. Règles : aucune adresse du site, aucune cote, pas de
courbe de momentum, ITF jamais, choix du match du jour inchangé."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
HTML = (RACINE / 'algo' / 'index.html').read_text(encoding='utf-8')
FILM = HTML[HTML.index('function momentsForts('):HTML.index('/* ───────────── carte de stats (?carte=1)')]
YML = (RACINE / '.github' / 'workflows' / 'video_simulation.yml').read_text(encoding='utf-8')
SCRIPT = (RACINE / 'scripts' / 'video_simulation.py').read_text(encoding='utf-8')

JS = r"""
const fs = require('fs');
const h = fs.readFileSync(process.argv[2], 'utf-8');
const bout = (a, b) => h.slice(h.indexOf(a), h.indexOf(b, h.indexOf(a)));
eval(bout('function Moteur(sim){', 'const logit'));
eval(bout("const PTS = ['0','15','30','40'];", '/* Les probabilités'));
eval(bout('function momentsForts(', 'async function filmDuJour'));
let a = 7; const R = () => { a = (a * 16807) % 2147483647; return a / 2147483647; };
const out = [];
for (const [pa, pb, n] of [[0.66, 0.62, 2], [0.64, 0.63, 2], [0.7, 0.58, 3]]) for (let k = 0; k < 30; k++) {
  const M = Moteur({ a: pa, b: pb, sets_gagnants: n, tb_final: 7 });
  // une trace complète tirée au hasard, comme le scénario de la vitrine
  const S = M.etat(k % 2); let tr = '';
  while (!S.fini) { const r = R(); const h0 = M.point(S, r); tr += String(h0); }
  const F = momentsForts(M, tr, k % 2, 5);
  out.push({ n: F.choix.length, quoi: F.choix.map(x => x.quoi), i: F.choix.map(x => x.i), fini: F.final.fini,
             vainqueur: F.final.vainqueur, dernier_h: F.choix[F.choix.length - 1].h, total: tr.length });
}
console.log(JSON.stringify(out));
"""


@unittest.skipUnless(shutil.which('node'), 'node absent')
class MomentsForts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'm.js'; f.write_text(JS, encoding='utf-8')
            r = subprocess.run(['node', str(f), str(RACINE / 'algo' / 'index.html')], capture_output=True, text=True, timeout=120)
            if r.returncode:
                raise AssertionError(r.stderr[-1500:])
            cls.R = json.loads(r.stdout)

    def test_la_balle_de_match_est_toujours_la_fin(self):
        for x in self.R:
            self.assertTrue(x['fini'])
            self.assertEqual(x['quoi'][-1], 'match')
            self.assertEqual(x['dernier_h'], x['vainqueur'])                  # le vrai vainqueur du match simulé
            self.assertEqual(x['i'][-1], x['total'] - 1)

    def test_peu_de_moments_dans_l_ordre(self):
        for x in self.R:
            self.assertTrue(2 <= x['n'] <= 6, x)
            self.assertEqual(x['i'], sorted(x['i']))
            self.assertEqual(len(set(x['i'])), len(x['i']))

    def test_ce_sont_des_moments_forts(self):
        quoi = [q for x in self.R for q in x['quoi']]
        for q in ('break', 'set', 'match'):
            self.assertIn(q, quoi)
        self.assertTrue(set(quoi) <= {'match', 'bm_sauvee', 'set', 'break', 'bs_sauvee', 'bb_sauvee', 'echange'})


class Regles(unittest.TestCase):
    def test_pas_d_adresse_ni_cote_ni_courbe(self):
        bas = FILM.lower()
        for mot in ('adresse', 'v_url', 'workers.dev', 'github.io', 'cote', 'pinnacle', 'march', 'value', ' pari'):
            self.assertNotIn(mot, bas, mot)
        self.assertNotIn('pLive', FILM)                                          # pas de % qui bouge pendant la vidéo
        self.assertNotIn('jauge', FILM)

    def test_itf_jamais_et_repli_2d(self):
        self.assertIn("!/ITF/i.test(m.circuit || '')", HTML)
        self.assertIn("Q.get('rendu') === '3d' && sd == null", HTML)            # un autre tirage : la vidéo 2D
        self.assertIn('G3D.disponible()) return filmDuJour(V, m, son);', HTML)

    def test_match_du_jour_inchange(self):
        self.assertIn("uid = uid_demande or (d.get('match_du_jour') or {}).get('uid') or ''", YML)

    def test_simulation_affichee(self):
        self.assertIn("t('a_sim')", FILM)                                        # « SIMULATION ×20 000 » toute la vidéo
        self.assertIn("t('a_fin_p'", FILM)


class Chaine(unittest.TestCase):
    def test_script_3d_par_defaut(self):
        self.assertIn("ap.add_argument('--rendu', default='3d'", SCRIPT)
        self.assertIn("'--enable-unsafe-swiftshader'", SCRIPT)
        self.assertIn("attendre_pret=a.rendu == '3d'", SCRIPT)

    def test_workflow_en_parallele(self):
        self.assertIn('lang: [fr, en]', YML)
        self.assertIn('timeout-minutes: 50', YML)
        self.assertIn('--rendu "${{ inputs.rendu || \'3d\' }}"', YML)
        self.assertIn("for lang in ${{ matrix.lang }}; do", YML)
        self.assertIn("--ips \"${{ (inputs.rendu || '3d') == '3d' && '25' || '30' }}\"", YML)   # 25 i/s en 3D : rendu sans carte graphique

    def test_son_de_stade(self):
        sys.path.insert(0, str(RACINE / 'scripts'))
        import sons
        for nom in ('service', 'rebond', 'filet', 'applaudissements', 'ovation', 'foule_entree', 'volet', 'frappe0', 'frappe1'):
            self.assertTrue(nom in sons.SONS or nom in sons.STADE, nom)
        for nom in re.findall(r"son\('([a-z_0-9]+)'", FILM):
            self.assertTrue(nom in sons.SONS or nom in sons.STADE, nom)
        with tempfile.TemporaryDirectory() as d:
            f = os.path.join(d, 's.wav')
            sons.piste([(0.5, 'service'), (1.0, 'rebond'), (1.2, 'ovation')], 3, f, ambiance='stade')
            with wave.open(f) as w:
                self.assertEqual(w.getnframes(), 3 * sons.TAUX)


class RapportPublic(unittest.TestCase):
    def test_rapport_et_regle_de_retrait(self):
        txt = (RACINE / 'simulateur' / 'rapport_video_3d.json').read_text(encoding='utf-8'); d = json.loads(txt)
        for mot in ('cote', 'pinnacle', 'march', 'alcaraz', 'medvedev', 'sinner'):
            self.assertNotIn(mot, txt.lower())
        self.assertFalse(d['retrait_declenche']); self.assertTrue(d['balle_de_match_toujours_en_dernier'])
        import importlib.util
        spec = importlib.util.spec_from_file_location('cv3', RACINE / 'simulateur' / 'controle_video_3d.py'); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        self.assertFalse(m.retrait([{'quoi': ['break', 'match'], 'fin_ok': True}]))
        self.assertTrue(m.retrait([{'quoi': ['match'], 'fin_ok': True}]))
        self.assertTrue(m.retrait([{'quoi': ['break', 'set'], 'fin_ok': False}]))


if __name__ == '__main__':
    unittest.main()
