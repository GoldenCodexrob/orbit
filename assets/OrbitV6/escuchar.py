"""
🎤 ESCUCHAR.PY - Reconocimiento de voz con SpeechRecognition
Usa Google (necesita internet pero es rápido y confiable)
"""

import threading

import speech_recognition as sr


class Escuchar:
    """Reconoce voz usando Google Speech Recognition."""

    def __init__(self):
        self.reconocedor = sr.Recognizer()
        self.reconocedor.pause_threshold = 0.9      # silencio para dar frase por terminada
        self.reconocedor.non_speaking_duration = 0.5
        self.microfono = None
        self.disponible = False
        self._mic_lock = threading.Lock()  # Previene acceso concurrente al micrófono
        self._cargar()

    def _cargar(self):
        """Inicializa el micrófono y calibra el umbral de energía."""
        try:
            self.microfono = sr.Microphone()

            print("🎤 Calibrando micrófono...")
            with self.microfono as fuente:
                self.reconocedor.adjust_for_ambient_noise(fuente, duration=0.5)

            # Bajar el umbral al 70 % del calibrado para capturar palabras
            # cortas ("sí", "no", "orbit") que de otro modo se perdían.
            self.reconocedor.energy_threshold = max(
                150, self.reconocedor.energy_threshold * 0.7
            )
            print(f"   Umbral de energía: {self.reconocedor.energy_threshold:.0f}")

            self.disponible = True
            print("✅ Micrófono listo\n")
        except Exception as e:
            print(f"❌ Error con micrófono: {e}")
            print("   Verifica que tengas un micrófono conectado")
            self.disponible = False

    def escuchar(self, timeout=None, frase_max=4):
        """
        Escucha por el micrófono y devuelve el texto reconocido.

        Args:
            timeout:   Segundos máximos de espera a que empiece el habla (None = infinito).
            frase_max: Duración máxima de una frase en segundos.

        Returns:
            Texto reconocido, "__TIMEOUT__" si expira el timeout, o None.
        """
        if not self.disponible:
            return None

        with self._mic_lock:  # Acceso exclusivo: evita conflicto con escuchar_breve()
            try:
                with self.microfono as fuente:
                    print("🎤 Habla ahora...", end="", flush=True)
                    audio = self.reconocedor.listen(
                        fuente,
                        timeout=timeout,
                        phrase_time_limit=frase_max,
                    )

                texto = self.reconocedor.recognize_google(audio, language="es-ES")
                if texto:
                    print(f" → '{texto}'")
                return texto.strip() if texto else None

            except sr.WaitTimeoutError:
                # 8 segundos sin audio detectado → señal de timeout
                print(" (tiempo de espera agotado)")
                return "__TIMEOUT__"

            except sr.UnknownValueError:
                # No se entendió (ruido, silencio breve)
                print(" (no se entendió)")
                return None

            except sr.RequestError as e:
                print(f"\n❌ Error de conexión: {e}")
                print("   Verifica tu conexión a internet")
                return None

            except Exception as e:
                print(f"\n❌ Error: {e}")
                return None

    def escuchar_breve(self, timeout=1.0, frase_max=1.5):
        """
        Escucha brevemente para detectar la wake word mientras el bot habla.
        Usa acquire no bloqueante: si el micrófono está ocupado, retorna None
        inmediatamente en lugar de esperar.

        Returns:
            Texto reconocido o None (nunca devuelve "__TIMEOUT__").
        """
        if not self.disponible:
            return None

        adquirido = self._mic_lock.acquire(blocking=False)
        if not adquirido:
            return None  # Micrófono en uso, saltar este ciclo sin bloquear

        try:
            with self.microfono as fuente:
                audio = self.reconocedor.listen(
                    fuente,
                    timeout=timeout,
                    phrase_time_limit=frase_max,
                )
            return self.reconocedor.recognize_google(audio, language="es-ES")
        except Exception:
            return None
        finally:
            self._mic_lock.release()


# ============================================
# Test
# ============================================
if __name__ == "__main__":
    escucha = Escuchar()

    if not escucha.disponible:
        print("\n❌ No se pudo inicializar el micrófono")
        input("ENTER para salir...")
    else:
        print("Di algo:")
        texto = escucha.escuchar(frase_max=5)
        if texto:
            print(f"\n✅ Reconocí: '{texto}'")
        else:
            print("\n❌ No escuché nada")
        input("\nENTER para salir...")