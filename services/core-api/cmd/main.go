package main

import (
	"log"
	"os"

	"github.com/gofiber/fiber/v2"
)

func main() {
	app := fiber.New()

	app.Get("/health", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{"status": "ok", "service": "srave-core-api"})
	})

	// TODO: register route groups
	// handlers.RegisterSpatialRoutes(app)
	// handlers.RegisterAuditRoutes(app)
	// handlers.RegisterBillingRoutes(app)
	// handlers.RegisterMultilateralRoutes(app)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	log.Fatal(app.Listen(":" + port))
}
