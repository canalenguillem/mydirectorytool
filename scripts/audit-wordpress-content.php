<?php
/**
 * Auditoría de calidad reutilizable para directorios publicados en WordPress.
 *
 * Uso dentro del contenedor de WordPress:
 * php audit-wordpress-content.php [post_type]
 */

$wp_load_path = getenv('WP_LOAD_PATH') ?: '/var/www/html/wp-load.php';

if (!is_file($wp_load_path)) {
    fwrite(STDERR, "No se encontró wp-load.php en {$wp_load_path}\n");
    exit(1);
}

require $wp_load_path;

$post_type = isset($argv[1]) ? sanitize_key($argv[1]) : 'restaurante';

if (!post_type_exists($post_type)) {
    fwrite(STDERR, "El post type {$post_type} no existe\n");
    exit(1);
}

function mdt_audit_normalize(string $value): string
{
    $value = remove_accents(wp_strip_all_tags($value));
    $value = strtolower($value);

    return trim((string) preg_replace('/\s+/u', ' ', $value));
}

/**
 * @param array<string, array<int, array<string, mixed>>> $groups
 * @return array<string, array<int, array<string, mixed>>>
 */
function mdt_audit_only_duplicates(array $groups): array
{
    return array_filter(
        $groups,
        static fn(array $items): bool => count($items) > 1
    );
}

/**
 * @return array<string, string>
 */
function mdt_audit_title_patterns(): array
{
    return array(
        'lo_mejor_segun_clientes' => '/^lo mejor de .+, segun quienes ya se han sentado a su mesa$/u',
        'todo_el_mundo_habla'      => '/^¿?por que todo el mundo habla de .+\??$/u',
        'paella_sin_trampa'        => '/^paella con vistas al mar y sin trampa: asi es /u',
        'propuesta_con_sello'      => '/: una propuesta gastronomica con sello propio$/u',
        'parada_para_recordar'     => '/: una parada gastronomica para recordar$/u',
        'conviene_saber'           => '/^comer en .+: lo que conviene saber antes de ir$/u',
        'vale_la_pena'             => '/^vale la pena comer en .+: esto dicen sus clientes$/u',
        'experiencia_al_detalle'   => '/: una experiencia contada al detalle$/u',
    );
}

$post_ids = get_posts(
    array(
        'post_type'      => $post_type,
        'post_status'    => 'publish',
        'posts_per_page' => -1,
        'orderby'        => 'ID',
        'order'          => 'ASC',
        'fields'         => 'ids',
        'no_found_rows'  => true,
    )
);

$report = array(
    'generated_at' => gmdate('c'),
    'site_url'     => home_url('/'),
    'post_type'    => $post_type,
    'total'        => count($post_ids),
    'summary'      => array(
        'missing_thumbnail' => 0,
        'missing_gallery'   => 0,
        'missing_contact'   => 0,
        'missing_location'  => 0,
        'missing_excerpt'   => 0,
        'short_excerpt'     => 0,
        'long_title'        => 0,
        'short_content'     => 0,
    ),
    'title_patterns'          => array_fill_keys(array_keys(mdt_audit_title_patterns()), 0),
    'exact_duplicate_titles'  => array(),
    'exact_duplicate_excerpts'=> array(),
    'flags'                   => array(),
    'thin_terms'              => array(),
);

$title_groups = array();
$excerpt_groups = array();
$patterns = mdt_audit_title_patterns();

foreach ($post_ids as $post_id) {
    $post_id = (int) $post_id;
    $title = (string) get_the_title($post_id);
    $excerpt = trim((string) get_the_excerpt($post_id));
    $content = (string) get_post_field('post_content', $post_id);
    $normalized_title = mdt_audit_normalize($title);
    $normalized_excerpt = mdt_audit_normalize($excerpt);
    $word_count = str_word_count(wp_strip_all_tags(strip_shortcodes($content)));
    $item = array(
        'post_id' => $post_id,
        'title'   => $title,
        'url'     => get_permalink($post_id),
    );
    $item_flags = array();

    $title_groups[$normalized_title][] = $item;

    if ($normalized_excerpt !== '') {
        $excerpt_groups[$normalized_excerpt][] = $item;
    }

    foreach ($patterns as $pattern_name => $pattern) {
        if (preg_match($pattern, $normalized_title)) {
            $report['title_patterns'][$pattern_name]++;
            break;
        }
    }

    if (!has_post_thumbnail($post_id)) {
        $report['summary']['missing_thumbnail']++;
        $item_flags[] = 'missing_thumbnail';
    }

    if (trim((string) get_post_meta($post_id, 'place_gallery', true)) === '') {
        $report['summary']['missing_gallery']++;
        $item_flags[] = 'missing_gallery';
    }

    $contact_values = array(
        get_post_meta($post_id, 'telefono', true),
        get_post_meta($post_id, 'web', true),
        get_post_meta($post_id, 'email', true),
    );

    if (count(array_filter(array_map('trim', array_map('strval', $contact_values)))) === 0) {
        $report['summary']['missing_contact']++;
        $item_flags[] = 'missing_contact';
    }

    $municipio = trim((string) get_post_meta($post_id, 'municipio', true));
    $ciudad = trim((string) get_post_meta($post_id, 'ciudad', true));
    $latitude = trim((string) get_post_meta($post_id, 'latitud', true));
    $longitude = trim((string) get_post_meta($post_id, 'longitud', true));

    if (($municipio === '' && $ciudad === '') || $latitude === '' || $longitude === '') {
        $report['summary']['missing_location']++;
        $item_flags[] = 'missing_location';
    }

    if ($excerpt === '') {
        $report['summary']['missing_excerpt']++;
        $item_flags[] = 'missing_excerpt';
    } elseif (strlen($normalized_excerpt) < 90) {
        $report['summary']['short_excerpt']++;
        $item_flags[] = 'short_excerpt';
    }

    if (strlen($normalized_title) > 70) {
        $report['summary']['long_title']++;
        $item_flags[] = 'long_title';
    }

    if ($word_count < 300) {
        $report['summary']['short_content']++;
        $item_flags[] = 'short_content';
    }

    if (!empty($item_flags)) {
        $item['flags'] = $item_flags;
        $item['word_count'] = $word_count;
        $report['flags'][] = $item;
    }
}

$report['exact_duplicate_titles'] = mdt_audit_only_duplicates($title_groups);
$report['exact_duplicate_excerpts'] = mdt_audit_only_duplicates($excerpt_groups);

$taxonomies = get_object_taxonomies($post_type, 'objects');

foreach ($taxonomies as $taxonomy) {
    if (!$taxonomy->public) {
        continue;
    }

    $terms = get_terms(
        array(
            'taxonomy'   => $taxonomy->name,
            'hide_empty' => true,
        )
    );

    if (is_wp_error($terms)) {
        continue;
    }

    foreach ($terms as $term) {
        if ($term->count > 2) {
            continue;
        }

        $term_url = get_term_link($term);
        $report['thin_terms'][] = array(
            'taxonomy'       => $taxonomy->name,
            'term_id'        => $term->term_id,
            'name'           => $term->name,
            'count'          => $term->count,
            'has_description'=> trim(wp_strip_all_tags($term->description)) !== '',
            'url'            => is_wp_error($term_url) ? '' : $term_url,
        );
    }
}

echo wp_json_encode(
    $report,
    JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES
);
