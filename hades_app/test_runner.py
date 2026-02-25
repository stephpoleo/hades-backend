"""
Custom Test Runner para Hades Backend.

Muestra resultados de tests de forma clara y amigable,
suprimiendo warnings y ruido innecesario.
"""

import sys
import warnings
import logging
from unittest import TextTestResult, TextTestRunner
from django.test.runner import DiscoverRunner


class CleanTestResult(TextTestResult):
    """
    Resultado de test personalizado con formato limpio.
    """

    # Colores ANSI (funcionan en la mayoria de terminales)
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.verbosity = verbosity
        self.successes = []
        self.current_class = None

    def getDescription(self, test):
        """Obtiene descripcion limpia del test."""
        doc = test.shortDescription()
        if doc:
            # Extraer solo la primera linea del docstring
            return doc.split('\n')[0].strip()
        return str(test).split(' ')[0]

    def startTest(self, test):
        """Muestra el nombre del test al iniciar."""
        # Llamar a TestResult.startTest, no a TextTestResult.startTest
        # para evitar que imprima la descripcion del test
        from unittest import TestResult
        TestResult.startTest(self, test)

        # Mostrar nombre de la clase si cambio
        test_class = test.__class__.__name__
        if test_class != self.current_class:
            self.current_class = test_class
            if self.verbosity >= 1:
                self.stream.write(f'\n{self.CYAN}{self.BOLD}{test_class}{self.RESET}\n')
                self.stream.write(f'{self.CYAN}{"-" * len(test_class)}{self.RESET}\n')
                self.stream.flush()

    def addSuccess(self, test):
        """Registra test exitoso."""
        # No llamar a super() para evitar duplicar el output
        self.successes.append(test)
        if self.verbosity >= 2:
            self.stream.write(f'  {self.GREEN}[OK]{self.RESET} {self.getDescription(test)}\n')
            self.stream.flush()
        elif self.verbosity >= 1:
            self.stream.write(f'{self.GREEN}.{self.RESET}')
            self.stream.flush()

    def addError(self, test, err):
        """Registra error en test."""
        # Guardar el error pero no llamar a super() para evitar duplicar output
        self.errors.append((test, self._exc_info_to_string(err, test)))
        if self.verbosity >= 2:
            self.stream.write(f'  {self.RED}[ERROR]{self.RESET} {self.getDescription(test)}\n')
            self.stream.flush()
        elif self.verbosity >= 1:
            self.stream.write(f'{self.RED}E{self.RESET}')
            self.stream.flush()

    def addFailure(self, test, err):
        """Registra test fallido."""
        # Guardar el fallo pero no llamar a super() para evitar duplicar output
        self.failures.append((test, self._exc_info_to_string(err, test)))
        if self.verbosity >= 2:
            self.stream.write(f'  {self.RED}[FAIL]{self.RESET} {self.getDescription(test)}\n')
            self.stream.flush()
        elif self.verbosity >= 1:
            self.stream.write(f'{self.RED}F{self.RESET}')
            self.stream.flush()

    def addSkip(self, test, reason):
        """Registra test saltado."""
        # Guardar el skip pero no llamar a super() para evitar duplicar output
        self.skipped.append((test, reason))
        if self.verbosity >= 2:
            self.stream.write(f'  {self.YELLOW}[SKIP]{self.RESET} {self.getDescription(test)}\n')
            self.stream.flush()
        elif self.verbosity >= 1:
            self.stream.write(f'{self.YELLOW}s{self.RESET}')
            self.stream.flush()

    def printErrors(self):
        """Imprime errores y fallos de forma clara."""
        if self.verbosity >= 1:
            self.stream.write('\n')
            self.stream.flush()

        if self.errors:
            self.stream.write(f'\n{self.RED}{self.BOLD}=== ERRORES ==={self.RESET}\n')
            for test, traceback in self.errors:
                self.stream.write(f'\n{self.RED}ERROR:{self.RESET} {test}\n')
                # Mostrar solo las lineas relevantes del traceback
                lines = traceback.strip().split('\n')
                for line in lines[-5:]:  # Ultimas 5 lineas
                    self.stream.write(f'  {line}\n')
            self.stream.flush()

        if self.failures:
            self.stream.write(f'\n{self.RED}{self.BOLD}=== FALLOS ==={self.RESET}\n')
            for test, traceback in self.failures:
                self.stream.write(f'\n{self.RED}FALLO:{self.RESET} {test}\n')
                lines = traceback.strip().split('\n')
                for line in lines[-5:]:
                    self.stream.write(f'  {line}\n')
            self.stream.flush()


class CleanTestRunner(TextTestRunner):
    """Test runner con resultado limpio."""
    resultclass = CleanTestResult


class HadesTestRunner(DiscoverRunner):
    """
    Test Runner personalizado para Hades Backend.

    Caracteristicas:
    - Suprime warnings de Django, GCP y librerias externas
    - Muestra resultados con colores y simbolos claros
    - Resumen final con estadisticas
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def setup_test_environment(self, **kwargs):
        """Configura el entorno de tests suprimiendo ruido."""
        super().setup_test_environment(**kwargs)

        # Suprimir warnings molestos
        warnings.filterwarnings('ignore', category=DeprecationWarning)
        warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
        warnings.filterwarnings('ignore', category=ResourceWarning)
        warnings.filterwarnings('ignore', message='.*credentials.*')
        warnings.filterwarnings('ignore', message='.*GCP.*')
        warnings.filterwarnings('ignore', message='.*storage.*')

        # Silenciar loggers ruidosos
        logging.getLogger('django').setLevel(logging.ERROR)
        logging.getLogger('django.request').setLevel(logging.ERROR)
        logging.getLogger('django.db.backends').setLevel(logging.ERROR)
        logging.getLogger('google').setLevel(logging.CRITICAL)
        logging.getLogger('urllib3').setLevel(logging.CRITICAL)
        logging.getLogger('root').setLevel(logging.CRITICAL)

    def get_resultclass(self):
        return CleanTestResult

    def run_suite(self, suite, **kwargs):
        """Ejecuta la suite con el runner limpio."""
        runner = CleanTestRunner(
            verbosity=self.verbosity,
            failfast=self.failfast,
        )
        return runner.run(suite)

    def suite_result(self, suite, result, **kwargs):
        """Muestra resumen final."""
        # Colores
        GREEN = '\033[92m'
        RED = '\033[91m'
        YELLOW = '\033[93m'
        CYAN = '\033[96m'
        BOLD = '\033[1m'
        RESET = '\033[0m'

        total = result.testsRun
        passed = len(result.successes) if hasattr(result, 'successes') else total - len(result.failures) - len(result.errors)
        failed = len(result.failures)
        errors = len(result.errors)
        skipped = len(result.skipped)

        print(f'\n{BOLD}{"=" * 50}{RESET}')
        print(f'{BOLD}  RESUMEN DE TESTS{RESET}')
        print(f'{BOLD}{"=" * 50}{RESET}\n')

        print(f'  Total ejecutados:  {CYAN}{total}{RESET}')
        print(f'  {GREEN}+ Pasaron:{RESET}         {GREEN}{passed}{RESET}')

        if failed > 0:
            print(f'  {RED}x Fallaron:{RESET}        {RED}{failed}{RESET}')
        if errors > 0:
            print(f'  {RED}x Errores:{RESET}         {RED}{errors}{RESET}')
        if skipped > 0:
            print(f'  {YELLOW}o Saltados:{RESET}        {YELLOW}{skipped}{RESET}')

        print()

        if failed == 0 and errors == 0:
            print(f'{GREEN}{BOLD}  + TODOS LOS TESTS PASARON{RESET}\n')
        else:
            print(f'{RED}{BOLD}  x HAY TESTS FALLIDOS{RESET}\n')

        return super().suite_result(suite, result, **kwargs)
