projects=(
  mason_indie
  gregory_indie
  falfurrias_indie
  sinton_pirate_indie
  milton
  lyssy
  medina_lake
  hearn_road
  goodwin
  laureles
  utopia
  gears_harris
  hidden_valley
  carrizo_springs
  leaky
  medina
  muenster_indie
  continental
)

for project in "${projects[@]}"; do
  mise api:insert_devices "$project"
  mise api:insert_tags "$project"
done