<?php
// Utilidad del autograde (no modificar): analiza un archivo PHP con el tokenizador oficial.
$src = (string) file_get_contents($argv[1] ?? '');
$out = ['comentarios' => [], 'cadenas' => [], 'variables' => [], 'codigo' => ''];
foreach (token_get_all($src) as $t) {
    if (is_array($t)) {
        if ($t[0] === T_COMMENT || $t[0] === T_DOC_COMMENT) {
            $out['comentarios'][] = $t[1];
            continue;
        }
        if ($t[0] === T_CONSTANT_ENCAPSED_STRING) { $out['cadenas'][] = trim($t[1], "'\""); }
        if ($t[0] === T_VARIABLE) { $out['variables'][] = $t[1]; }
        $out['codigo'] .= $t[1];
    } else {
        $out['codigo'] .= $t;
    }
}
echo json_encode($out, JSON_UNESCAPED_UNICODE);
