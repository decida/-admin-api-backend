"""
Script para testar a criação de rotas dinâmicas.
Verifica se existem API Resources no banco e simula o refresh_dynamic_routes.
"""

import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.db.session import SessionLocal
from app.models.api_resource import ApiResource
from app.core.dynamic_routes import refresh_dynamic_routes, get_registered_routes

def test_dynamic_routes():
    """Test dynamic routes creation."""
    print("=" * 80)
    print("TESTING DYNAMIC ROUTES")
    print("=" * 80)

    db = SessionLocal()
    try:
        # 1. Check if there are API resources in DB
        print("\n1. Checking API Resources in database...")
        all_resources = db.query(ApiResource).all()
        active_resources = db.query(ApiResource).filter(ApiResource.is_active == True).all()

        print(f"   Total API Resources: {len(all_resources)}")
        print(f"   Active API Resources: {len(active_resources)}")

        if not all_resources:
            print("\n   [WARNING] NO API RESOURCES FOUND IN DATABASE!")
            print("   This is why dynamic routes are not being created.")
            return

        # 2. Show all resources
        print("\n2. API Resources details:")
        for resource in all_resources:
            status = "[ACTIVE]" if resource.is_active else "[INACTIVE]"
            print(f"   {status} | {resource.method:6} | {resource.path:40} | {resource.business_object_name}")

        # 3. Test refresh_dynamic_routes
        print("\n3. Testing refresh_dynamic_routes()...")
        refresh_dynamic_routes(db)

        # 4. Show registered routes
        registered = get_registered_routes()
        print(f"\n4. Registered dynamic routes: {len(registered)}")
        for path, resource_id in registered.items():
            print(f"   {path} -> {resource_id}")

        if len(registered) == 0:
            print("\n   [WARNING] NO ROUTES WERE REGISTERED!")
            print("   Checking for potential issues...")

            # Check for issues
            if len(active_resources) > 0:
                print("\n   There are active resources but routes weren't registered.")
                print("   Possible causes:")
                print("   - Exception during route registration (check logs)")
                print("   - Issue with path format")
                print("   - Issue with business_object relationship")
        else:
            print("\n   [OK] Routes registered successfully!")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

    print("\n" + "=" * 80)

if __name__ == "__main__":
    test_dynamic_routes()
