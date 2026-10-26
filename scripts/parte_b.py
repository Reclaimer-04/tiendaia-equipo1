import time
import requests

print("--- 1. Países (GraphQL) ---")
# GraphQL usa una sola URL y la consulta define qué campos queremos
consulta_paises = """
{
  countries(filter: {code: {in: ["MX", "AR", "BR", "CO", "PE", "CL", "ES", "US", "CA", "JP"]}}) {
    name
    capital
    currency
  }
}
"""
r_paises = requests.post("https://countries.trevorblades.com/", json={"query": consulta_paises}, timeout=10)
print(len(r_paises.content), "bytes")
print(r_paises.json())

print("\n--- 2. Pokémon (REST) ---")
nombres = ["pikachu", "bulbasaur", "charmander", "squirtle", "eevee", 
           "snorlax", "gengar", "onix", "psyduck", "jigglypuff"]

total_bytes, t = 0, time.perf_counter()
for n in nombres:
    r = requests.get(f"https://pokeapi.co/api/v2/pokemon/{n}", timeout=10)
    total_bytes += len(r.content)
ms_rest = (time.perf_counter() - t) * 1000
print("REST:", len(nombres), "peticiones,", total_bytes, "bytes,", f"{ms_rest:.0f} ms")


print("\n--- 3. Pokémon (GraphQL) ---")
consulta_poke = """
query {
  pokemon_v2_pokemon(where: {name: {_in: ["pikachu", "bulbasaur", "charmander", "squirtle", "eevee", "snorlax", "gengar", "onix", "psyduck", "jigglypuff"]}}) {
    name
    height
    pokemon_v2_pokemontypes {
      pokemon_v2_type {
        name
      }
    }
  }
}
"""
t = time.perf_counter()
r_poke = requests.post("https://graphql.pokeapi.co/v1beta2", json={"query": consulta_poke}, timeout=10)
ms_graphql = (time.perf_counter() - t) * 1000
print("GraphQL: 1 petición,", len(r_poke.content), "bytes,", f"{ms_graphql:.0f} ms")