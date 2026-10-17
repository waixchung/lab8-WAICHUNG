<?php
declare(strict_types=1);

define('SEMILLA_LAB8', 'WEB2026-L8');
const LAB_NUMERO = 8;

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

// Mostrar los valores y tipos de datos calculados anteriormente.
var_dump($codigo, $n1, $precio, $activo, $nulo, $lista);

// Sumar dos cadenas que contienen números.
$suma_str = "5" + "10"; #Imprime el valor de la operación aritmética indicada.

// Concatenar dos cadenas de texto.
$concat = "5" . "10"; #Imprime los dos dígitos juntos, pues en PHP el . se usa para concatenar.

// Convertir una cadena al tipo entero.
$cast_int = (int) "12abc"; #Convierte la parte numérica inicial de la cadena en entero.

// Comparar números decimales.
$float_eq = (0.1 + 0.2 == 0.3); #Declara como falso ya que los decimales pueden tener pequeñas diferencias de precisión en su representación binaria.

// Comparación flexible entre dos cadenas.
$loose = ("10" == "1e1"); #PHP interpreta ambas cadenas como números: 10 y 1e1 (10).

// Comparación estricta entre dos cadenas.
$strict = ("10" === "1e1"); #Compara estrictamente ambas cadenas, que contienen textos diferentes.

$resultado = [
    'codigo' => $codigo,
    'n1' => $n1,
    'n2' => $n2,
    'suma' => $suma,
    'division' => $division,
    'resto' => $resto,
    'cociente' => $cociente,
    'precio' => $precio,
    'activo' => $activo,

    // Obtenemos los tipos de datos de las variables.
    'tipos' => [
        'codigo' => gettype($codigo),
        'n1' => gettype($n1),
        'precio' => gettype($precio),
        'activo' => gettype($activo),
        'nulo' => gettype($nulo),
        'lista' => gettype($lista)
    ],

    // Guardamos los resultados de las conversiones y comparaciones.
    'juggling' => [
        'suma_str' => $suma_str,
        'concat' => $concat,
        'cast_int' => $cast_int,
        'float_eq' => $float_eq,
        'loose' => $loose,
        'strict' => $strict
    ],

    // Consultamos las constantes y comprobamos su redefinicion.
    'constantes' => [
        'SEMILLA_LAB8' => constant('SEMILLA_LAB8'),
        'LAB_NUMERO' => LAB_NUMERO,
        'redefinir' => @define('SEMILLA_LAB8', 'otra')
    ]
];

// Imprimimos una linea identificable para el autograde.
echo "\n##JSON## " . json_encode($resultado) . "\n";