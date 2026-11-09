package main

import (
	"log"
	"os"

	"github.com/gofiber/fiber/v2"
)

func main() {
	app := fiber.New()

	app.Get("/health", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{"status": "ok", "service": "srave-multilateral-api"})
	})

	// TODO: register multilateral routes
	// handlers.RegisterMultilateralRoutes(app)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8003"
	}
	log.Fatal(app.Listen(":" + port))
}
