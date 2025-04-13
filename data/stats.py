import json
from datetime import datetime

# Charger les statistiques depuis le fichier
def load_stats(file_path='data/stats.json'):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            'total_views': 0,
            'category_views': {},
            'product_views': {},
            'last_updated': datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            'last_reset': datetime.utcnow().strftime("%Y-%m-%d")
        }

# Sauvegarder les statistiques dans le fichier
def save_stats(stats, file_path='data/stats.json'):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=4, ensure_ascii=False)

# Nettoyer les statistiques des produits et catégories qui n'existent plus
def clean_stats(catalog, stats):
    # Nettoyer les vues par catégorie
    if 'category_views' in stats:
        categories_to_remove = []
        for category in stats['category_views']:
            if category not in catalog:
                categories_to_remove.append(category)
        
        for category in categories_to_remove:
            del stats['category_views'][category]
            print(f"🧹 Suppression des stats de la catégorie: {category}")

    # Nettoyer les vues par produit
    if 'product_views' in stats:
        categories_to_remove = []
        for category in stats['product_views']:
            if category not in catalog:
                categories_to_remove.append(category)
                continue
            
            products_to_remove = []
            existing_products = [p['name'] for p in catalog[category]]
            
            for product_name in stats['product_views'][category]:
                if product_name not in existing_products:
                    products_to_remove.append(product_name)
            
            for product in products_to_remove:
                del stats['product_views'][category][product]
                print(f"🧹 Suppression des stats du produit: {product} dans {category}")
            
            if not stats['product_views'][category]:
                categories_to_remove.append(category)
        
        for category in categories_to_remove:
            if category in stats['product_views']:
                del stats['product_views'][category]

    stats['last_updated'] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    save_stats(stats)

# Incrémenter les statistiques pour un produit
def increment_product_views(catalog, category, product_name):
    stats = load_stats()
    
    if 'product_views' not in stats:
        stats['product_views'] = {}
    if category not in stats['product_views']:
        stats['product_views'][category] = {}
    if product_name not in stats['product_views'][category]:
        stats['product_views'][category][product_name] = 0

    stats['product_views'][category][product_name] += 1
    stats['total_views'] += 1
    stats['last_updated'] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    save_stats(stats)