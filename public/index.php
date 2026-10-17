<?php
declare(strict_types=1);

// 1. Cargamos la librería que permite leer los datos del estudiante.
require_once __DIR__ . '/../lib/estudiante.php';

// 2. Obtenemos la información almacenada en estudiante.json.
$est = cargar_estudiante();

# 3. Establecemos la zona horaria de Panamá.
date_default_timezone_set('America/Panama');

/*
  4. Guardamos en variables los datos que utilizaremos
  para construir el contenido de nuestra página HTML.
*/
$nombre = $est['nombre'];
$apellido = $est['apellido'];

// 5. Obtenemos la versión actual de PHP.
$version = PHP_VERSION;

# 6. Generamos la fecha y hora con el formato solicitado.
$fecha = date('d/m/Y H:i');
?>
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <!-- 7. Generamos el título de la página con PHP. -->
    <title>Lab 8 - <?php echo htmlspecialchars($apellido); ?></title>
</head>
<body>

    <!-- 8. Mostramos el nombre completo como encabezado principal. -->
    <h1>
        <?php echo htmlspecialchars($nombre . ' ' . $apellido); ?>
    </h1>

    <!-- Mostramos la versión de PHP instalada en el servidor. -->
    <p>
        Versión de PHP:
        <?php print htmlspecialchars($version); ?>
    </p>

    <!-- Mostramos la fecha y hora actual de Panamá. -->
    <p>
        Fecha y hora actual:
        <?= htmlspecialchars($fecha) ?>
    </p>

</body>
</html>