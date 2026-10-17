<?php
declare(strict_types=1);

define('SEMILLA_LAB8', 'WEB2026-L8');
const Lab_NUMERO = 8;

require_once __DIR__ . '/../lib/estudiante.php';
$est = cargar_estudiante();

// Generar una huella SHA-256 a partir de mi cédula y la semilla.
$huella = hash('sha256', $est['cedula'] . '|' . SEMILLA_LAB8);

// Obtener los primeros 8 caracteres de la huella.
$codigo = substr($huella, 0, 8);

// Obtener los caracteres 8 y 9 de la huella y convertirlos a entero.
$n1 = hexdec(substr($huella, 8, 2)) % 90 + 10;

// Obtener los caracteres 10 y 11 de la huella y convertirlos a entero.
$n2 = hexdec(substr($huella, 10, 2)) % 90 + 10;

// Generar un precio con dos decimales.
$precio = round(hexdec(substr($huella, 12, 4)) / 100, 2);

// Determinar si n1 es par.
$activo = ($n1 % 2 === 0);

// Sumar los dos números.
$suma = $n1 + $n2;

// Dividir n1 entre n2 y redondear a dos decimales.
$division = round($n1 / $n2, 2);

// Obtener el residuo de la división.
$resto = $n1 % $n2;

// Obtener el cociente entero.
$cociente = intdiv($n1, $n2);

// Crear una variable sin valor.
$nulo = null;

// Crear un arreglo con tres números enteros.
$lista = [1, 2, 3];