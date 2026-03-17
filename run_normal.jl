using Pkg; Pkg.activate(".")
using Images, CausticsEngineering

TARGET_IMAGE = get(ENV, "COW2_INPUT", "./examples/befuddled_cow_solver_input.jpg")
println("Loading: $TARGET_IMAGE")
image = Images.load(TARGET_IMAGE)
image = imresize(image, (512, 512))
println("Resized to 512x512 — mesh will be ~525k faces")
engineer_caustics(image)
