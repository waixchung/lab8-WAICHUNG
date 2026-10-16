<?php
declare(strict_types=1);

/**
 * Lee estudiante.json (raíz del repositorio) y devuelve un arreglo con:
 * nombre, apellido, cedula, github_user.
 * Esta función te la damos hecha; úsala con require_once.
 */
function cargar_estudiante(): array
{
    $ruta = __DIR__ . '/../estudiante.json';
    $datos = json_decode((string) file_get_contents($ruta), true);
    if (!is_array($datos)) {
        throw new RuntimeException('estudiante.json no es un JSON válido');
    }
    return $datos;
}
