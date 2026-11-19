"""Exécuteur Docker commun (Tâche 3).

Une seule interface pour PHP et Python, côté « legacy » (PHP 7.4 / Python 2.7)
et côté « modern » (PHP 8.3 / Python 3.12). Le code inconnu s'exécute dans un
conteneur sans réseau, avec des limites de mémoire, de CPU et de processus.
"""
import os
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

DOCKER_DIR = Path(__file__).resolve().parent / "docker"

# (langage, côté) -> (nom de l'image, Dockerfile)
ENVIRONMENTS = {
    ("python", "legacy"): ("smartmigrator-py27", "py27.Dockerfile"),
    ("python", "modern"): ("smartmigrator-py312", "py312.Dockerfile"),
    ("php", "legacy"): ("smartmigrator-php74", "php74.Dockerfile"),
    ("php", "modern"): ("smartmigrator-php83", "php83.Dockerfile"),
}


@dataclass
class RunResult:
    ok: bool            # code de retour 0 et pas de dépassement de temps
    stdout: str
    stderr: str
    returncode: int
    timed_out: bool = False


def docker_available() -> bool:
    """True si le démon Docker répond."""
    try:
        return subprocess.run(["docker", "info"], capture_output=True,
                              timeout=15).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def build_image(language: str, side: str) -> str:
    """Construit l'image si elle n'existe pas encore. Renvoie son nom."""
    image, dockerfile = ENVIRONMENTS[(language, side)]
    exists = subprocess.run(["docker", "image", "inspect", image],
                            capture_output=True)
    if exists.returncode != 0:
        print(f"  ... construction de l'image {image} (première fois seulement)",
              flush=True)
        subprocess.run(["docker", "build", "-t", image, "-f",
                        str(DOCKER_DIR / dockerfile), str(DOCKER_DIR)], check=True)
    return image


def script_command(language: str, filename: str) -> list:
    """Commande qui exécute un fichier seul."""
    if language == "python":
        return ["python", filename]
    return ["php", "-d", "display_errors=stderr", filename]


def run_in_docker(language: str, side: str, files: dict, command: list,
                  timeout: int = 30, memory: str = "256m",
                  cpus: str = "1") -> RunResult:
    """Écrit `files` ({chemin: contenu}) dans un dossier temporaire monté en /work,
    puis exécute `command` dans le conteneur du bon environnement."""
    image = build_image(language, side)
    name = f"sm-{uuid.uuid4().hex[:8]}"
    folder = tempfile.mkdtemp(prefix="smartmigrator_")
    try:
        for filename, content in files.items():
            target = Path(folder) / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        user = ["--user", f"{os.getuid()}:{os.getgid()}"] if hasattr(os, "getuid") else []
        docker_command = [
            "docker", "run", "--rm", "--name", name,
            "--network", "none",                 # aucun accès réseau
            "--memory", memory, "--cpus", cpus,  # limites de ressources
            "--pids-limit", "128",
            "--security-opt", "no-new-privileges",
            *user, "-e", "HOME=/tmp",
            "-v", f"{folder}:/work", "-w", "/work",
            image, *command,
        ]
        try:
            run = subprocess.run(docker_command, capture_output=True, text=True,
                                 encoding="utf-8", errors="replace", timeout=timeout)
        except subprocess.TimeoutExpired:
            subprocess.run(["docker", "kill", name], capture_output=True)
            return RunResult(False, "", f"timeout après {timeout} s", -1, timed_out=True)
        return RunResult(run.returncode == 0, run.stdout, run.stderr, run.returncode)
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def run_script(language: str, side: str, filename: str, code: str,
               timeout: int = 30) -> RunResult:
    """Exécute un programme (un seul fichier) dans l'environnement demandé."""
    return run_in_docker(language, side, {filename: code},
                         script_command(language, filename), timeout)