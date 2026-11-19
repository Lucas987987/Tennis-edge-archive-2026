"""Public du stade (paquet 300, 19/11/2026, Lucas : « le bruit du public, ce n'est pas du tout clair »). L'ancien
public était du bruit filtré ; il est maintenant fait de voix synthétiques (hauteur, voyelles, syllabes) et
d'applaudissements au rythme de chaque spectateur. Toujours rien d'enregistré."""
import sys
import time
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
try:
    import numpy as np
    import scipy  # noqa: F401
    SCIPY = True
except ImportError:
    SCIPY = False


@unittest.skipUnless(SCIPY, 'scipy absent')
class PublicStade(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(RACINE / 'scripts'))
        import sons_stade
        cls.S = sons_stade

    def test_des_voix_et_pas_du_souffle(self):
        S = self.S
        r = S._rng(3)
        x = S._bouche(S._source(int(0.4 * S.TAUX), 120.0, r), S.VOYELLES['a'])
        x = x - x.mean()
        ac = np.correlate(x[:8000], x[:8000], 'full')[7999:]
        periode = int(S.TAUX / 120)
        self.assertGreater(ac[periode - 5:periode + 5].max() / ac[0], 0.5)       # une hauteur nette (voix), pas un bruit

    def test_applaudissements_rythmes(self):
        S = self.S
        x = S.applaudir(2.0, 40, 0.5, S._rng(1))                                  # 10 spectateurs
        self.assertEqual(x.shape, (2 * S.TAUX, 2))
        self.assertTrue(np.isfinite(x).all())
        self.assertLessEqual(np.abs(x).max(), 0.5 + 1e-9)
        env = np.abs(x[:, 0]).reshape(-1, 480).max(axis=1)                         # 10 ms par case
        self.assertGreater((env > 0.05 * env.max()).mean(), 0.2)

    def test_brouhaha_et_ovation(self):
        S = self.S
        t = time.time()
        b = S.brouhaha(20, S._rng(5))
        self.assertLess(time.time() - t, 30)                                      # 75 s de vidéo : quelques secondes
        self.assertEqual(b.shape, (20 * S.TAUX, 2))
        self.assertLess(np.corrcoef(b[S.TAUX:-S.TAUX, 0], b[S.TAUX:-S.TAUX, 1])[0, 1], 0.5)   # vraie stéréo
        o = S.ovation(3.8, S._rng(9))
        self.assertTrue(np.isfinite(o).all())
        self.assertGreater(len(o), 3.5 * S.TAUX)
        h = S.houle(S._rng(8))
        self.assertEqual(h.shape[1], 2)

    def test_rien_d_enregistre(self):
        src = (RACINE / 'scripts' / 'sons_stade.py').read_text(encoding='utf-8')
        self.assertNotIn('wavfile.read', src)
        self.assertIn('paquet 300', src)


if __name__ == '__main__':
    unittest.main()
