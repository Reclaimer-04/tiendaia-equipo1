import time
import requests

consulta = """
{ countries(filter: {code: {in: ["MX", "AR", "BR", "CO", "PE",
"CL", "ES", "US", "CA", "JP"]}}) {
  name
  capital
  currency
} }
"""

t = time.perf_counter()
r = requests.post("https://countries.trevorblades.com/",
                  json={"query": consulta}, timeout=10)
ms = (time.perf_counter() - t) * 1000
print("Countries GraphQL:", r.status_code, f"{ms:.0f} ms", len(r.content), "bytes")
print(r.json())


nombres = ["pikachu", "bulbasaur", "charmander", "squirtle", "eevee",
           "snorlax", "gengar", "onix", "psyduck", "jigglypuff"]

total_bytes, t = 0, time.perf_counter()
for n in nombres:
    r = requests.get(f"https://pokeapi.co/api/v2/pokemon/{n}", timeout=10)
    total_bytes += len(r.content)
ms = (time.perf_counter() - t) * 1000
print("REST:", len(nombres), "peticiones,", total_bytes, "bytes,", f"{ms:.0f} ms")


consulta = """
{
  pokemon_v2_pokemon(where: {name: {_in: ["pikachu","bulbasaur","charmander",
  "squirtle","eevee","snorlax","gengar","onix","psyduck","jigglypuff"]}}) {
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
r = requests.post("https://beta.pokeapi.co/graphql/v1beta",
                  json={"query": consulta}, timeout=10)
ms = (time.perf_counter() - t) * 1000
print("GraphQL:", 1, "petición,", len(r.content), "bytes,", f"{ms:.0f} ms")

try:
    print(r.json())
except requests.exceptions.JSONDecodeError:
    print("Respuesta no es JSON:", r.text)
