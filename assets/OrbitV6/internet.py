"""
Módulo de búsquedas web (intenta varias fuentes).

Correcciones:
  ISSUE-10  Los bare `except:` capturaban KeyboardInterrupt y SystemExit,
            impidiendo salir con Ctrl+C durante una búsqueda lenta.
            Sustituidos por `except requests.RequestException` que solo
            captura errores de red y HTTP.
"""

import re
import requests


class BusquedaWeb:
    def __init__(self):
        self.sesion = requests.Session()
        self.sesion.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        self.timeout = 8

    def hay_internet(self) -> bool:
        """Comprueba conectividad intentando alcanzar Bing."""
        try:
            self.sesion.get("https://www.bing.com", timeout=3)
            return True
        except requests.RequestException:
            return False

    def buscar(self, query: str) -> list:
        """Intenta DuckDuckGo y Bing; devuelve lista de resultados o []."""
        for url, params in [
            ("https://html.duckduckgo.com/html/", {"q": f"Venezuela {query} niños"}),
            ("https://www.bing.com/search", {"q": f"Venezuela {query} niños"}),
        ]:
            try:
                r = self.sesion.get(url, params=params, timeout=self.timeout)
                if r.status_code == 200 and len(r.text) > 1000:
                    text = re.sub(r'<[^>]+>', ' ', r.text)
                    sentences = re.findall(r'[A-Z][^.]*Venezuela[^.]*\.', text)
                    if sentences:
                        return [{
                            "titulo": "Búsqueda web",
                            "contenido": ' '.join(sentences[:3])[:500]
                        }]
            except requests.RequestException:
                continue
        return []

    def buscar_resumen(self, query: str) -> str | None:
        """Devuelve el primer resultado como string, o None si no hay resultados."""
        resultados = self.buscar(query)
        if resultados:
            return resultados[0]['contenido']
        return None