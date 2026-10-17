<?php
declare(strict_types=1);
require_once __DIR__ . '/../lib/estudiante.php';

$est = cargar_estudiante();
$cfg = require __DIR__ . '/../config/db.php';

$db = new mysqli(
    $cfg['host'],
    $cfg['user'],
    $cfg['pass'],
    $cfg['name'],
    (int) $cfg['port']
);
// Obtener la versión de MariaDB
$db_version = $db->query('SELECT VERSION()')->fetch_row()[0];

// Obtener el nombre de la base de datos
$db_nombre = $db->query('SELECT DATABASE()')->fetch_row()[0];

// Contar los estudiantes
$filas = (int) $db->query('SELECT COUNT(*) FROM estudiantes')->fetch_row()[0];

// Obtener los primeros 10 caracteres del hash
$token = substr(hash('sha256', $est['cedula'] . '.'), 0, 10);

// Si NO es consola, avisa que la respuesta es JSON:
if (PHP_SAPI !== 'cli') {
    header('Content-Type: application/json; charset=utf-8');
}

echo json_encode([
    'php_version' => PHP_VERSION,
    'sapi' => php_sapi_name(),
    'os_family' => PHP_OS_FAMILY,
    'servidor' => $_SERVER['SERVER_SOFTWARE'] ?? 'cli',
    'mysqli' => extension_loaded('mysqli'),
    'db_version' => $db_version,
    'db_nombre' => $db_nombre,
    'filas' => $filas,
    'token' => $token
], JSON_PRETTY_PRINT);